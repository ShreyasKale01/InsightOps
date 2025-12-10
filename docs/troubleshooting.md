# Troubleshooting

### `ANTHROPIC_API_KEY is not set`
You haven't configured `.env`. Run `cp .env.example .env` and add a real key from https://console.anthropic.com/.

### `CSV file not found: ...`
Check the path is relative to where you're running `python main.py` from, or use an absolute path. `data/sample_sales.csv` is included for a quick test.

### `Dataset has N rows, exceeding the configured MAX_ROWS=200000`
Either raise `MAX_ROWS` in `.env` if you genuinely need to load that much into memory, or pre-aggregate/filter the data (e.g., with a `WHERE`/`LIMIT` in SQL, or a smaller CSV export) before loading.

### `Invalid filter expression: ...` or the model's filter tool calls keep failing
The model likely referenced a column name that doesn't exist, or used invalid pandas `query()` syntax (e.g., unquoted string literals). This is expected to self-correct within the loop — check `result.tool_calls` in the returned `AgentResult` to see the exact expression that failed and why.

### Agent returns "I reached the maximum number of analysis steps..."
The question may be too broad for the configured `AGENT_MAX_TURNS` (default 8), or the model is looping. Try narrowing the question, or increase `AGENT_MAX_TURNS` in `.env` (this increases worst-case cost/latency per question).

### Charts aren't appearing
Check `OUTPUT_DIR` in `.env` (default `outputs/`) and that the process has write permission there. In Docker, make sure `outputs/` is mounted as a volume (see `docker-compose.yml`), otherwise generated files are lost when the container exits.

### `DATABASE_URL is not set` when using `--sql`
Set `DATABASE_URL` in `.env` to a SQLAlchemy-compatible connection string for your database (e.g., `postgresql+psycopg2://user:pass@host:5432/db`).

### Tests fail with an import error
Make sure you've run `pip install -r requirements.txt` in the same environment you're running `pytest` from, and that you're running `pytest` from the project root (not from inside `tests/`).
