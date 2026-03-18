# SPS Confidence Checklist

Use this checklist before claiming a targeted confidence pass for the current SPS v2 build.

- Bootstrap the local environment with `scripts/bootstrap_dev.sh`.
- Start local services with `docker compose up -d`.
- Run `scripts/run_confidence_checks.sh`.
- Confirm package manifest verification passed.
- Confirm release bundle dry run completed successfully.
- Confirm targeted pytest suites passed.
- Confirm the test scenario has no open release blockers for the success path.
