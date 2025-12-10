# Setup Guide

## 1. Prerequisites

- Python 3.12 or later
- pip
- (Optional) Docker + Docker Compose
- An Anthropic API key from https://console.anthropic.com/

## 2. Clone and install

```bash
git clone <YOUR_GITHUB_URL>/ai-data-analyst-agent.git
cd ai-data-analyst-agent
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

All other variables have sensible defaults (see `.env.example` for details).

## 4. Verify the install

Run the test suite — this does not require an API key, since tests mock the Claude client:

```bash
pytest tests/ -v
```

You should see 19 passed.

## 5. Run against the sample dataset

```bash
python main.py --file data/sample_sales.csv \
  --question "Which region generated the most revenue?" \
  --report
```

## 6. (Optional) Connect a database

Set `DATABASE_URL` in `.env` to a SQLAlchemy-compatible connection string, e.g.:

```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/analytics
```

Then run with `--sql` instead of `--file`:

```bash
python main.py --sql "SELECT * FROM orders" --question "What is the average order value?"
```

## 7. (Optional) Run with Docker

```bash
docker compose up --build
```

This builds the image, mounts `data/` read-only and `outputs/` writable, and runs the default demo question defined in `docker-compose.yml`.
