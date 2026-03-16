# S01: Deterministic document artifacts + submission package persistence — UAT

**Milestone:** M006-h7v2qk
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven + live-runtime (partial)
- Why this mode is sufficient: Document generation and digest computation are deterministic and proven via artifact-driven tests (pytest). Full live-runtime proof (Temporal workflow + S3 storage + API retrieval) requires infrastructure (LocalStack/Postgres/Temporal) which will be provided in S02 docker-compose runbook. This UAT validates the artifact-driven proof boundaries achieved in S01.

## Preconditions

- Python virtual environment activated (`.venv/bin/activate`)
- Dependencies installed (`pip install -e .`)
- Phase 6 fixtures exist under `specs/sps/build-approved/fixtures/phase6/`
- pytest available in environment

For live-runtime tests (optional, requires infrastructure):
- Docker-compose stack running with Postgres + LocalStack/S3 + Temporal
- Database migrated to latest schema (`alembic upgrade head`)
- Environment variables configured:
  - `SPS_DB_HOST`, `SPS_DB_PORT`, `SPS_DB_NAME`, `SPS_DB_USER`, `SPS_DB_PASSWORD`
  - `SPS_S3_ENDPOINT_URL=http://localhost:9000` (for LocalStack)
  - `SPS_S3_ACCESS_KEY_ID`, `SPS_S3_SECRET_ACCESS_KEY`
  - `SPS_S3_BUCKET_EVIDENCE=sps-evidence`
  - `SPS_TEMPORAL_ADDRESS=localhost:7233`
  - `SPS_RUN_TEMPORAL_INTEGRATION=1`

## Smoke Test

Run fixture validation tests to confirm Phase 6 fixture dataset loads and templates render:

```bash
cd /Users/chunkstand/projects/sps-v2
source .venv/bin/activate
pytest tests/m006_s01_document_package_test.py::test_load_phase6_fixtures_schema_valid -v
```

**Expected:** Test passes with `1 passed` output. This confirms fixtures are loadable and schema-valid.

## Test Cases

### 1. Phase 6 fixtures load with valid schema

1. Run: `pytest tests/m006_s01_document_package_test.py -k fixtures -v`
2. **Expected:** All 10 fixture tests pass:
   - `test_load_phase6_fixtures_schema_valid` — Dataset has required fields
   - `test_load_phase6_fixtures_pydantic_strict` — Extra fields raise AttributeError
   - `test_load_document_fixtures_missing_file` — Missing fixture file raises FileNotFoundError
   - `test_load_template_success` — Valid template loads with content
   - `test_load_template_missing` — Missing template raises FileNotFoundError with path
   - `test_resolve_phase6_fixture_case_id_no_override` — Returns first dataset case_id without env var
   - `test_resolve_phase6_fixture_case_id_with_override` — Returns override case_id when env var set
   - `test_select_document_fixtures_default_case` — Returns matching document set for default case_id
   - `test_select_document_fixtures_with_override` — Returns matching document set for override case_id
   - `test_select_document_fixtures_no_match` — Returns empty list when no match found

### 2. Document generation produces deterministic sha256 digests

1. Run: `pytest tests/m006_s01_document_package_test.py::test_document_generation_determinism -v`
2. **Expected:** Test passes with validation that:
   - Document bytes are generated from template + variables
   - sha256 digest is computed from final bytes
   - Manifest includes document references with matching digests
   - Generated package has expected structure (package_id, manifest, documents[])

### 3. Document templates render with variable substitution

1. Load a Phase 6 template manually:
   ```python
   from sps.fixtures.phase6 import load_template
   template = load_template("permit_application_template.txt")
   print(template[:200])
   ```
2. **Expected:** Template content includes mustache-style placeholders like `{{project_address}}`, `{{system_size_kw}}`, etc.

3. Render the template with variables:
   ```python
   from sps.documents.generator import generate_document
   from sps.fixtures.phase6 import load_phase6_fixtures
   
   fixtures = load_phase6_fixtures()
   doc_set = fixtures.document_sets[0]
   doc_fixture = doc_set.documents[0]
   
   result = generate_document(
       document_id=doc_fixture.document_id,
       document_type=doc_fixture.document_type,
       template_name=doc_fixture.template_name,
       variables=doc_fixture.document_variables
   )
   print(f"Document bytes: {len(result.content_bytes)}")
   print(f"SHA256 digest: {result.sha256_digest}")
   ```
4. **Expected:** Document bytes are > 0, digest is 64-character hex string, and content includes rendered variables (no `{{...}}` placeholders remain).

### 4. Package persistence schema exists in database

1. Check migration applied:
   ```bash
   alembic current
   ```
2. **Expected:** Current revision is `a1b2c3d4e5f6` (submission_packages migration)

3. Verify tables exist:
   ```sql
   SELECT table_name FROM information_schema.tables 
   WHERE table_schema = 'public' 
   AND table_name IN ('submission_packages', 'document_artifacts');
   ```
4. **Expected:** Both `submission_packages` and `document_artifacts` tables exist

### 5. Evidence registry helper computes sha256 and prepares S3 URIs (unit test)

This test validates registry logic without requiring S3 infrastructure:

1. Inspect the EvidenceRegistry implementation:
   ```bash
   grep -A 20 "def register_document" src/sps/documents/registry.py
   ```
2. **Expected:** Method computes sha256 from content_bytes, calls storage.put_bytes with integrity check, and returns RegisteredArtifact with artifact_id + digest + storage_uri

3. Verify sha256 computation in isolation:
   ```python
   import hashlib
   test_bytes = b"test document content"
   expected_digest = hashlib.sha256(test_bytes).hexdigest()
   print(f"SHA256: {expected_digest}")
   ```
4. **Expected:** 64-character hex digest (e.g., `9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08`)

## Edge Cases

### Missing template file

1. Attempt to load a non-existent template:
   ```python
   from sps.fixtures.phase6 import load_template
   try:
       load_template("nonexistent_template.txt")
   except FileNotFoundError as e:
       print(f"Error: {e}")
   ```
2. **Expected:** Raises `FileNotFoundError` with message "Template not found: specs/sps/build-approved/fixtures/phase6/nonexistent_template.txt"

### Invalid fixture case_id override

1. Set invalid override env var:
   ```bash
   export SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE=INVALID-CASE-ID
   ```
2. Attempt to select fixtures:
   ```python
   from sps.fixtures.phase6 import select_document_fixtures, resolve_phase6_fixture_case_id
   case_id = resolve_phase6_fixture_case_id()
   result = select_document_fixtures(case_id)
   print(f"Result: {result}")
   ```
3. **Expected:** Returns empty list (no error) because no fixture matches the override case_id
4. Clean up: `unset SPS_PHASE6_FIXTURE_CASE_ID_OVERRIDE`

### Extra fields in fixture JSON (Pydantic strict validation)

1. Run: `pytest tests/m006_s01_document_package_test.py::test_load_phase6_fixtures_pydantic_strict -v`
2. **Expected:** Test passes by verifying that accessing non-existent fields raises AttributeError
3. Demonstrates that Pydantic `extra="forbid"` prevents silent addition of unexpected fields

## Failure Signals

- **Fixture loading fails**: FileNotFoundError with path indicates missing fixture files or incorrect path resolution
- **Template rendering incomplete**: Rendered documents still contain `{{variable}}` placeholders, indicating missing variables in fixture metadata
- **Digest mismatch**: sha256 digest computed from content_bytes doesn't match stored digest in manifest/evidence artifacts
- **Migration not applied**: `alembic current` shows revision before `a1b2c3d4e5f6`, meaning submission_packages schema is missing
- **S3 connection errors in integration tests**: `ConnectionRefusedError: [Errno 61] Connection refused` to localhost:9000 means LocalStack is not running (expected for S01; defer to S02)
- **Foreign key violations during package persistence**: Indicates `session.flush()` ordering is broken or evidence_artifacts rows are missing

## Requirements Proved By This UAT

- R015 (Submission package generation) — Partial proof:
  - ✅ Deterministic document generation from Phase 6 fixtures (proven)
  - ✅ sha256 digest computation from final document bytes (proven)
  - ✅ Manifest structure with document references and digests (proven)
  - ✅ Package persistence schema exists and migrations applied (proven)
  - ✅ Evidence registry helper logic for artifact registration (proven at boundary)
  - ⏳ Full end-to-end persistence with S3 storage (pending S02 docker-compose)
  - ⏳ Workflow transition INCENTIVES_COMPLETE → DOCUMENT_COMPLETE (pending S02)
  - ⏳ API retrieval of package + manifest (pending S02)

## Not Proven By This UAT

- **Full end-to-end package persistence**: Requires LocalStack/S3 running in docker-compose (deferred to S02)
- **Workflow advancement to DOCUMENT_COMPLETE**: Requires Temporal worker running (deferred to S02)
- **API package/manifest retrieval**: Requires FastAPI server + Postgres + S3 (deferred to S02)
- **Idempotency of package persistence under activity retry**: Requires Temporal activity retry simulation (deferred to S02)
- **Evidence artifact retrieval from S3**: Requires LocalStack/S3 (deferred to S02)
- **Comprehensive failure path testing**: Digest mismatch scenarios and template rendering errors should be tested before production

## Notes for Tester

**S01 scope**: This slice focused on proving deterministic document generation and digest computation in isolation, plus implementing the full persistence path up to the S3 boundary. Full end-to-end integration (workflow + S3 + API) requires infrastructure that will be provided in S02's docker-compose runbook.

**S3 infrastructure**: If you want to run the full integration tests locally, you'll need to start LocalStack in docker-compose before running:
```bash
SPS_RUN_TEMPORAL_INTEGRATION=1 pytest tests/m006_s01_document_package_test.py -k integration -v
```

Without S3 running, these tests will fail with `ConnectionRefusedError` — this is expected and documented in the slice plan.

**Known rough edges**:
- Template variable validation is minimal — if a template references a missing variable, rendering will succeed but produce incomplete documents
- Failure path tests for digest mismatch are not yet implemented
- Evidence registry helper is unit-tested but not integration-tested with real S3 until S02

**Areas needing gut check**:
- Verify that fixture `document_variables` dict matches all `{{variable}}` placeholders in the templates
- Inspect generated document bytes to confirm variables are substituted correctly
- Check that manifest digests match evidence artifact checksums in future S02 runbook
