"""
Centralized configuration loaded from environment variables.

No secrets are hardcoded anywhere in this project. All configuration
is read from the environment (populated via a local `.env` file in
development, or real environment variables / secrets manager in
production).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a local .env file if present. In production,
# real environment variables (injected by Docker/K8s/CI) take priority
# and are not overwritten by .env.
load_dotenv(override=False)


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"Environment variable {name} must be an integer, got: {raw!r}")


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    agent_model: str = field(default_factory=lambda: os.getenv("AGENT_MODEL", "claude-sonnet-4-6"))
    agent_max_turns: int = field(default_factory=lambda: _get_int("AGENT_MAX_TURNS", 8))

    database_url: str | None = field(default_factory=lambda: os.getenv("DATABASE_URL"))

    output_dir: Path = field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "outputs")))
    max_rows: int = field(default_factory=lambda: _get_int("MAX_ROWS", 200_000))

    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    def validate_for_live_run(self) -> None:
        """Raise a clear, actionable error if required config is missing.

        Called only when the agent actually needs to call the LLM API
        (not required for pure data-loading / unit-testable code paths).
        """
        if not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and "
                "add your key from https://console.anthropic.com/"
            )

    def ensure_output_dir(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir


def get_settings() -> Settings:
    return Settings()


def configure_logging(level: str | None = None) -> None:
    logging.basicConfig(
        level=(level or get_settings().log_level).upper(),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
