"""
AI Data Analyst Agent core.

Implements a bounded tool-calling loop against the Anthropic Messages
API: the model is given a dataset schema + a natural-language question,
it calls structured tools (see tools.py) to inspect/filter/aggregate/
chart the data, and finally returns a written analysis plus any charts
it generated.

The loop is bounded by `max_turns` (see config.AGENT_MAX_TURNS) to
guarantee termination and cap cost even if the model tries to keep
calling tools indefinitely.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import anthropic
import pandas as pd

from .config import Settings, get_settings
from .tools import TOOL_REGISTRY, ToolError, get_schema

logger = logging.getLogger(__name__)

# JSON-schema tool definitions handed to the model. Kept in sync by hand
# with the function signatures in tools.py (df / output_dir are injected
# by the agent, never exposed to the model).
TOOL_DEFINITIONS = [
    {
        "name": "get_schema",
        "description": "Return column names, dtypes, null counts, and cardinality for the loaded dataset. Call this first if you have not already seen the schema.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "describe_data",
        "description": "Return summary statistics (count, mean, std, min, quartiles, max) for numeric columns.",
        "input_schema": {
            "type": "object",
            "properties": {
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of columns to restrict the summary to. Omit to cover all numeric columns.",
                }
            },
        },
    },
    {
        "name": "filter_data",
        "description": "Filter rows with a pandas boolean query expression, e.g. \"revenue > 1000 and region == 'US'\". Returns matched row count and a 10-row preview, not the full dataset.",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "Pandas query() expression."}},
            "required": ["expression"],
        },
    },
    {
        "name": "aggregate_data",
        "description": "Group rows by one or more columns and aggregate a numeric metric (sum, mean, median, count, min, max, std). Use this for 'top N by X', 'total by category', trend-by-group, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "group_by": {"type": "array", "items": {"type": "string"}},
                "metric_column": {"type": "string", "description": "Numeric column to aggregate. Ignored if agg_func is 'count'."},
                "agg_func": {"type": "string", "enum": ["sum", "mean", "median", "count", "min", "max", "std"]},
                "top_n": {"type": "integer", "description": "Optional: limit to the top N rows by the aggregated value."},
            },
            "required": ["group_by", "metric_column", "agg_func"],
        },
    },
    {
        "name": "create_chart",
        "description": "Render a chart (bar, line, scatter, hist, pie) to a PNG file and return its path. Optionally aggregates by group_by first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {"type": "string", "enum": ["bar", "line", "scatter", "hist", "pie"]},
                "x": {"type": "string"},
                "y": {"type": "string"},
                "title": {"type": "string"},
                "group_by": {"type": "array", "items": {"type": "string"}},
                "agg_func": {"type": "string", "enum": ["sum", "mean", "median", "count", "min", "max"], "default": "sum"},
            },
            "required": ["chart_type", "title"],
        },
    },
]

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "system_prompt.txt"


@dataclass
class AgentResult:
    answer: str
    chart_paths: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    turns_used: int = 0


class DataAnalystAgent:
    """Bounded tool-calling loop that turns a question + DataFrame into
    a written analysis and, optionally, charts."""

    def __init__(self, df: pd.DataFrame, settings: Settings | None = None):
        self.df = df
        self.settings = settings or get_settings()
        self.settings.validate_for_live_run()
        self.client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)
        self.output_dir = self.settings.ensure_output_dir()

    def _system_prompt(self) -> str:
        base = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8") if SYSTEM_PROMPT_PATH.exists() else (
            "You are a meticulous data analyst. Use the provided tools to inspect and "
            "analyze the dataset before answering. Never invent numbers you have not "
            "computed via a tool call."
        )
        schema = get_schema(self.df)
        return f"{base}\n\nDataset schema:\n{json.dumps(schema, indent=2)}"

    def _dispatch_tool(self, name: str, tool_input: dict) -> dict:
        fn = TOOL_REGISTRY.get(name)
        if fn is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            if name == "get_schema":
                return fn(self.df)
            if name == "create_chart":
                return fn(self.df, output_dir=self.output_dir, **tool_input)
            return fn(self.df, **tool_input)
        except ToolError as exc:
            logger.warning("Tool %s failed: %s", name, exc)
            return {"error": str(exc)}
        except TypeError as exc:
            logger.warning("Tool %s called with invalid arguments: %s", name, exc)
            return {"error": f"Invalid arguments for {name}: {exc}"}

    def analyze(self, question: str) -> AgentResult:
        """Run the bounded tool-calling loop for a single natural-language question."""
        messages: list[dict] = [{"role": "user", "content": question}]
        chart_paths: list[str] = []
        tool_call_log: list[dict] = []
        turns = 0

        for turns in range(1, self.settings.agent_max_turns + 1):
            response = self.client.messages.create(
                model=self.settings.agent_model,
                max_tokens=2000,
                system=self._system_prompt(),
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            if response.stop_reason != "tool_use":
                final_text = "".join(block.text for block in response.content if block.type == "text")
                return AgentResult(
                    answer=final_text.strip(),
                    chart_paths=chart_paths,
                    tool_calls=tool_call_log,
                    turns_used=turns,
                )

            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                logger.info("Model called tool: %s(%s)", block.name, block.input)
                result = self._dispatch_tool(block.name, block.input)
                tool_call_log.append({"tool": block.name, "input": block.input, "result": result})
                if block.name == "create_chart" and "chart_path" in result:
                    chart_paths.append(result["chart_path"])
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    }
                )
            messages.append({"role": "user", "content": tool_results})

        logger.warning("Agent hit max_turns=%s without a final answer.", self.settings.agent_max_turns)
        return AgentResult(
            answer=(
                "I reached the maximum number of analysis steps before finishing. "
                "Here is what I found from the tool calls so far; consider narrowing "
                "the question or increasing AGENT_MAX_TURNS."
            ),
            chart_paths=chart_paths,
            tool_calls=tool_call_log,
            turns_used=turns,
        )
