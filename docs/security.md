# Security

## Threat model

The primary threat this project defends against is a **misbehaving or prompt-injected LLM attempting to execute arbitrary code or exfiltrate data** through the analysis pipeline. Secondary concerns are secret handling and safe defaults for resource use.

## Controls implemented

| Threat | Control |
|---|---|
| Arbitrary code execution via the model | No `eval`/`exec` exposed. The model can only call 5 fixed functions with JSON-schema-validated arguments. |
| SQL/expression injection via `filter_data` | Expression is rejected if it contains `;`, `` ` ``, or any of a denylist of tokens (`import`, `os.`, `sys.`, `eval(`, `exec(`, `open(`, `subprocess`, `globals`, `locals`, `__`). Length capped at 300 chars. |
| Arbitrary SQL via `--sql` / `load_sql` | Only queries starting with `SELECT` or `WITH` are accepted; anything else raises `DataLoadError` before reaching the database. |
| Unbounded memory/cost from huge inputs | `MAX_ROWS` guard in both `load_csv` and `load_sql`; `AGENT_MAX_TURNS` bounds the number of LLM calls per question. |
| Secret leakage | No secrets in code or docs. `.env` is gitignored; `.env.example` documents variable names only. `Settings.validate_for_live_run()` fails fast with a clear message if `ANTHROPIC_API_KEY` is missing, rather than the key silently being `None` deep in a request. |
| Bulk data exfiltration into LLM context/logs | Tool results are intentionally compact: `filter_data` returns a 10-row preview and a count, never the full filtered set; `aggregate_data` returns aggregates, not raw rows. |
| Container compromise blast radius | Docker image runs as non-root `appuser`; `data/` is mounted read-only in `docker-compose.yml`. |

## Known gaps (honest, not hidden)

- **No authentication/authorization layer.** This is currently a CLI/library, not a multi-tenant hosted service. If exposed as an API in the future, it needs API-key auth, per-key rate limiting, and per-request audit logging before pointing it at real customer data — see [Future Improvements](../README.md#future-improvements).
- **Denylist, not a sandbox.** `filter_data`'s token denylist is a pragmatic control appropriate for a CLI tool used by its owner, not a formally verified sandbox. It should not be treated as sufficient isolation for fully untrusted multi-tenant input without an additional layer (e.g., a restricted expression parser or a proper sandboxed subprocess).
- **No PII classification.** The agent does not currently detect or redact PII columns before they're summarized/charted. If used on data containing PII, review column sensitivity before running.
- **Prompt injection via dataset content.** If a dataset itself contains adversarial text (e.g., a "product name" engineered to look like an instruction), the system prompt's rule to only report tool-computed numbers limits — but does not eliminate — the risk of the model being steered. This is an active area for the [AI evaluation harness](../README.md#future-improvements) future improvement.

## Reporting

This is a personal portfolio project; there is no formal responsible-disclosure process. For questions, reach out via the contact details in the [README](../README.md#author).
