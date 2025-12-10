# Contributing

This is currently a personal portfolio project by Sohag Gain, but issues and PRs are welcome.

## Development setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install ruff
cp .env.example .env  # add your ANTHROPIC_API_KEY to actually run the agent
```

## Before submitting a PR

```bash
ruff check src/ tests/ main.py
pytest tests/ -v
```

Both must pass cleanly. New tool functions should include:
- A unit test for the happy path and at least one error path in `tests/unit/test_tools.py`.
- An update to `docs/api.md` describing the new tool contract.
- If the tool is exposed to the model, add it to `TOOL_DEFINITIONS` in `src/agent/core.py` with a clear `description` field.

## Commit style

Use clear, imperative commit messages (e.g., "Add median support to aggregate_data", not "fix stuff").
