# CERT_48 frozen-engine hash closure

**Historical decision: UNRESOLVABLE — CASE D.** The expected historical hashes were not changed. This file and the diff CSV remain the record of the old baseline investigation; the old manifest is classified as `UNRESOLVED_LEGACY_BASELINE` and is no longer the active engine gate.

## Reproduction and hash contract

`tests/application/test_historical_shares_units.py::test_shares_unit_020_frozen_engine` was run independently and failed deterministically. It reads `tests/fixtures/cvm/shares_unit_v1/manifest.json` and computes `hashlib.sha256((ROOT / path).read_bytes()).hexdigest()`. This is SHA-256 over raw file bytes; there is no normalization. The protected file set and expected/actual values are recorded in [frozen_engine_hash_diff.csv](frozen_engine_hash_diff.csv).

The isolated test fails on `magic_formula_ranking_validation.py`: expected `47140198ac099487f4160be411c46ef549a1d3ac3e8db25dbbc672d7133e6a37`, actual `039656c877d516ce2e2cdcf5d6bba7efadf948a92958875ecd140a16349ce83d`. `magic_formula_contract.py` also mismatches (`9e299489a57c049fcbcc940a0d3fdfa573d174cc8c57b97c14f4fcc63204163f` expected; `40b1def756c8cde12f556835ac7e989adab18907b1a0d7364aff3bfd6aa032f9` actual). `magic_formula_stocks.py` matches. All three source files are clean in the working tree.

## Git provenance and semantics

The two mismatching source files and `manifest.json` first appear together in commit `4d5781ce1d09b8317207f653e0bde8e5a4580cc9` (`feat: restore analytics platform capabilities and migrations`, 2026-10-17). No earlier version of either source file or the manifest is present in reachable Git history. The V2 work did not touch these files; they predate the V2 baseline. Thus the first repository-observable mismatch is the introducing commit itself, but the repository cannot establish a prior matching revision or which side represents the intended approved implementation.

The fixture README describes the manifest as recording hashes of the unchanged ranking engine and canonical contract. Repository search found no canonical generator for the `frozen_code_sha256` entries; this is test-fixture metadata, not a release artifact. Since no hash-matching implementation is available for a semantic diff, both mismatches are classified `UNKNOWN`. Updating the manifest would assume the current files are authoritative, while restoring source from an unavailable version would also be guesswork. Neither action is justified by the evidence.

Current share/unit protections remain directly exercised by the historical-share-unit regression suite: explicit document-bound quantity units, ON/PN/UNIT class identity, issued and treasury quantities, and fail-closed unresolved evidence. The 22-file Magic Formula regression selection completed with **326 passed, 1 failed**; its sole failure was CERT_48. This confirms the surrounding tests pass against the current behavior but cannot prove equivalence to an unavailable prior frozen version. It does not justify changing methodology or financial semantics.

## Canonical Magic Formula reconciliation

Existing canonical artifacts remain aligned: policy `MF_BR_2027_V1`, policy hash `96d5d54ab1b1320ddc14f1a3c9cd6764b1bf8d68f1e6d79ffd0faa6d1b72cbac`, active snapshot `mf-f1ee50809c83979ba221d84e`, ranking hash `f1ee50809c83979ba221d84ebb48150b9470331240940f89a8cb745f2a4ee8f3`, 165 ranked companies, and canonical result SHA-256 `162c1b2f8856ae7d88cf5809d9418395464d0b2042bf6177fb48141e5b4fcf6a`. All 165 rows in the existing snapshot contain EY, ROC and global rank. The snapshot was not regenerated.

The focused V2 isolation suite was rerun and passed **20/20** (3 existing deprecation warnings). The previous complete suite result remains **882 passed, 1 failed, 6 warnings**, with the single failure being this hash guard; a full suite was not repeated because no correction was made.

## Required disposition

`CERT_48 = INCOMPLETE`. Do not update the frozen hashes, change implementation semantics, regenerate the ranking, or proceed to V3 on this evidence. To close the gate, recover the approved hash-matching source/manifest from its authoritative origin (for example, a pre-restoration archive or signed release artifact), then compare behavior and outputs against that source. Until such provenance exists, stop here.
