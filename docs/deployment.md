# Deployment

## Current status: Deployment-ready CLI/container, not hosted

This project ships as a runnable CLI and a Docker image. There is no live-hosted URL (see [Limitations](../README.md#limitations)); the sections below describe how it can be deployed and run today, and the realistic next step to make it a hosted service.

## Local / scheduled use

```bash
python main.py --file data/sample_sales.csv --question "..." --report
```

Suitable for ad-hoc runs or a cron job producing a daily/weekly markdown report.

## Docker

```bash
docker build -t ai-data-analyst-agent .
docker run --env-file .env \
  -v $(pwd)/data:/app/data:ro \
  -v $(pwd)/outputs:/app/outputs \
  ai-data-analyst-agent --file data/sample_sales.csv --question "..." --report
```

Or via Compose:

```bash
docker compose up --build
```

## Health checks

For a scheduled/batch use case like this, "health" is defined as: the container exits with status 0 and a report file exists in `outputs/`. A monitoring wrapper (cron + alerting, or a CI scheduled workflow) should check both.

## Path to a hosted service (future work)

To move from CLI to a hosted API (not yet implemented):

1. Wrap `DataAnalystAgent` in a FastAPI app with an `/analyze` endpoint.
2. Add API-key authentication and per-key rate limiting.
3. Add structured request/response logging (question asked, tool calls made, latency, token usage) for observability and cost tracking.
4. Deploy the container to a managed compute service (e.g., AWS ECS/Fargate or a similar container platform) behind a load balancer, with `ANTHROPIC_API_KEY` and `DATABASE_URL` injected via a secrets manager rather than a mounted `.env` file.
5. Add a CloudWatch (or equivalent) alarm on error rate and p95 latency.

This is intentionally not built yet — the honest status is CLI/Docker only, matching the [no-fabrication rule](../README.md) in this portfolio.
