# Prospective frozen-engine baseline generator

Generator: `scripts/generate_magic_formula_frozen_engine_baseline.py`.

The generator is intentionally narrow. Its protected source set is declared in `PROTECTED_FILES`; it hashes raw bytes using SHA-256, normalizes paths to repository-relative POSIX form, and sorts all file entries. It refuses to produce a baseline if the active policy fingerprint or published canonical ranking reconciliation differs from the V9.2/V12.2/V2 anchors.

The deterministic payload contains the baseline ID, source Git commit, policy and canonical ranking identities, protected file hashes, policy-artifact hashes, semantic-contract version/hash, golden cases and test file hashes, relevant Magic Formula test manifest, and Python/pytest metadata. The payload is serialized as UTF-8 compact JSON with sorted keys before its SHA-256 is calculated. `created_at_utc` is outer creation metadata and is excluded from the deterministic payload hash.

Run from the repository root:

```powershell
py -3.14 scripts/generate_magic_formula_frozen_engine_baseline.py
```

The output is `docs/appendices/multiportfolio_v2_certification_closure/frozen_engine_baseline_v2.json`. Reproducibility is checked by generating two temporary documents from the same tree, then comparing `payload`, `payload_sha256`, protected-file hashes and test-manifest hashes. The pytest regression repeats the payload check and verifies every protected file against the published baseline. A legitimate engine or golden-test change requires an explicit reviewed baseline regeneration; the historical manifest is never overwritten.
