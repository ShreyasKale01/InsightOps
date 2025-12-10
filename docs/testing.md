# Testing

## Philosophy

- **No live API calls in tests.** The Anthropic client is monkeypatched with a scripted fake in integration tests, so the suite is free, fast, deterministic, and runs in CI without a real API key.
- **Data/tool layers are pure and independently tested.** `data_loader.py` and `tools.py` have zero AI dependency, so their unit tests exercise real pandas behavior directly.
- **Security-relevant behavior has explicit tests** (e.g., `test_filter_data_rejects_dangerous_input`, `test_filter_data_rejects_semicolon`) — these aren't incidental, they're the regression guard for the security boundary described in `docs/security.md`.

## Running the suite

```bash
pytest tests/ -v
pytest tests/ -v --cov=src/agent --cov-report=term-missing   # with coverage
```

Current status: **19/19 passing**.

## Test breakdown

| File | What it covers |
|---|---|
| `tests/unit/test_data_loader.py` | CSV happy path, missing file, empty file, row-limit guard, schema summarization shape. |
| `tests/unit/test_tools.py` | Every tool's happy path (schema, describe, filter, aggregate, chart) and its error paths, including the two security-denial tests. |
| `tests/integration/test_agent.py` | Full tool-calling loop with a scripted fake Claude client: one tool call then a final answer, and a runaway-loop scenario verifying `AGENT_MAX_TURNS` actually terminates the loop. |

## What's intentionally not tested

- Real Claude API responses (would require a live key, cost money, and be non-deterministic — not appropriate for CI). Manual smoke testing against the real API is recommended before each release using `data/sample_sales.csv`.
- Chart visual correctness (pixel-level assertions on matplotlib output are brittle); tests instead assert the file was created at the expected path.
