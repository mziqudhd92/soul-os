# Scripts

| Script | Purpose |
|--------|---------|
| `seed.py` | Register example souls and ingest sample facts (`npm run seed`, kernel on :8000). |
| `soulos-doctor.py` | Preflight kernel + inference (`python scripts/soulos-doctor.py`). |
| `run-tests.sh` | Run kernel + gateway test suites. |
| `doc-gen/generate_docs.py` | Regenerate `docs/reference/architecture.md` from template. |
| `doc-gen/bundle_agent_context.py` | Print compact agent context path; `--full` writes `docs/SOULOS_AGENT_CONTEXT_FULL.md` (gitignored). |
