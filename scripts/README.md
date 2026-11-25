# Reproduce the lab evidence

Run Python inside WSL from the repository root. Use the Python environment installed from Part 6 requirements and Part 7 develop requirements. Docker Desktop must integrate with WSL.

- `python scripts/run_local_benchmarks.py`: collect v1/v2 eval and seven load reports. Preserve the original KB when reproducing the baseline; the submitted KB is already fixed.
- `python scripts/run_local_benchmarks.py --fixed`: evaluate the fixed v2 against reports/eval_v2.json.
- `python scripts/collect_mission_evidence.py`: run Part 1 and Part 4 HTTP examples on separate ports; redact JWT.
- `python scripts/run_production_experiments.py`: use the running observability stack, measure exact 1/3 replicas with --no-deps, run combined error/latency chaos, large model, pause and v1 eval. Recreates lab agent containers; wait until complete before cleanup.
- `python scripts/collect_traces.py`: capture a real slow/error trace through Jaeger v3 API and matching log excerpts.
- `python scripts/write_benchmark_report.py`, then `python scripts/finalize_benchmark_report.py`: derive tables from JSON/CSV. The first command rebuilds the report, so preserve any manually added context before rerunning it.
- `python scripts/check_public_deployment.py --url https://YOUR-SERVICE.onrender.com`: cloud checks. Uses getpass to prompt for the API key; does not save the key.

Screenshot helpers use Node.js, Playwright and an installed Microsoft Edge. Install/provide Playwright separately; set PLAYWRIGHT_MODULE to its module path if it is not on Node's module search path. Screenshots capture actual Grafana/Jaeger/Prometheus pages.

`cache_lab_images.py` is an optional workaround for Docker daemon pull EOF errors: it builds an image containing only FROM for each official image tag through BuildKit. A separate local DOCKER_CONFIG with empty auths worked around the WSL Windows credential helper error in this run. No personal Docker credentials are changed.

Keep .env, API keys and login tokens outside Git. JSON report errors/SLO failures are evidence and must not be edited to fabricate a pass. A nonzero Locust exit with mock upstream errors can still produce valid CSV.
