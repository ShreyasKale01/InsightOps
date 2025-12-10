# Changelog

All notable changes to this project are documented here.

## [0.1.0] - 2026-08-07

### Added
- Initial release: bounded Claude tool-calling loop with 5 pandas-backed tools (`get_schema`, `describe_data`, `filter_data`, `aggregate_data`, `create_chart`).
- CSV and read-only SQL data loading with row-count safety guard.
- Markdown report generation with embedded chart references and tool-call audit trail.
- CLI (`main.py`) supporting `--file` and `--sql` sources.
- Docker + docker-compose setup.
- GitHub Actions CI (lint + test + Docker build).
- 19 passing unit/integration tests; security-focused tests for the `filter_data` denylist.
- Full documentation set: architecture, setup, API/tool reference, security, testing, deployment, troubleshooting.
