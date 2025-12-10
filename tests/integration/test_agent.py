"""
Integration test for the DataAnalystAgent tool-calling loop.

We do NOT call the real Anthropic API in tests (no network, no cost,
deterministic). Instead we monkeypatch `anthropic.Anthropic` with a
fake client that scripts a realistic two-turn conversation: turn 1
calls the aggregate_data tool, turn 2 returns a final text answer.
This verifies the loop's wiring (message history, tool dispatch,
result formatting, termination) without depending on a live model.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agent.config import Settings


@dataclass
class FakeToolUseBlock:
    id: str
    name: str
    input: dict
    type: str = "tool_use"


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeResponse:
    content: list
    stop_reason: str


class FakeMessages:
    def __init__(self, scripted_responses):
        self._responses = list(scripted_responses)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        return self._responses.pop(0)


class FakeAnthropicClient:
    def __init__(self, scripted_responses, api_key=None):
        self.messages = FakeMessages(scripted_responses)


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "region": ["US", "US", "EU", "EU"],
            "revenue": [100.0, 300.0, 50.0, 20.0],
        }
    )


def test_agent_completes_tool_call_loop(monkeypatch, sample_df, tmp_path):
    scripted = [
        FakeResponse(
            content=[
                FakeToolUseBlock(
                    id="tool_1",
                    name="aggregate_data",
                    input={"group_by": ["region"], "metric_column": "revenue", "agg_func": "sum"},
                )
            ],
            stop_reason="tool_use",
        ),
        FakeResponse(
            content=[FakeTextBlock(text="US has the highest total revenue at $400.")],
            stop_reason="end_turn",
        ),
    ]

    import agent.core as core_module

    monkeypatch.setattr(
        core_module.anthropic,
        "Anthropic",
        lambda api_key=None: FakeAnthropicClient(scripted, api_key=api_key),
    )

    settings = Settings(anthropic_api_key="fake-key-for-test", output_dir=tmp_path)
    agent = core_module.DataAnalystAgent(sample_df, settings=settings)

    result = agent.analyze("Which region has the highest total revenue?")

    assert "US" in result.answer
    assert result.turns_used == 2
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["tool"] == "aggregate_data"


def test_agent_stops_at_max_turns(monkeypatch, sample_df, tmp_path):
    """If the model never stops calling tools, the loop must still terminate."""
    looping_response = FakeResponse(
        content=[FakeToolUseBlock(id="t", name="get_schema", input={})],
        stop_reason="tool_use",
    )

    import agent.core as core_module

    monkeypatch.setattr(
        core_module.anthropic,
        "Anthropic",
        lambda api_key=None: FakeAnthropicClient([looping_response] * 3, api_key=api_key),
    )

    settings = Settings(anthropic_api_key="fake-key-for-test", output_dir=tmp_path, agent_max_turns=3)
    agent = core_module.DataAnalystAgent(sample_df, settings=settings)

    result = agent.analyze("Loop forever")

    assert result.turns_used == 3
    assert "maximum" in result.answer.lower()
