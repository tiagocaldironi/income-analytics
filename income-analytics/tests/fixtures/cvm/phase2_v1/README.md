# Phase 2 CVM fixtures, version 1

These are unchanged Latin-1, semicolon-delimited row excerpts from the official
2025 DFP and ITR archives already cached in `data/cvm`. The manifest records the
source URLs, archive SHA-256, excerpt SHA-256, reference dates and issuer sample.
The original cache retrieval timestamp is unknown; no new retrieval is claimed.

The sample is the five issuers in `MAGIC_FORMULA_REAL_DATA_VALIDATION_REPORT.md`:
Votorantim Cimentos (027189), Vale (004170), Localiza Fleet (024813), MRV (020915),
and Ambev (023264). Localiza Fleet is deliberately not substituted with its parent.

DFP reference: 2025-12-31. ITR reference: 2025-09-30. All consolidated BPA, BPP and
DRE rows for those issuers/dates are retained, including comparison periods and
quarter/YTD rows. Original columns, filing versions, currency scale and descriptions
remain intact. Tests reconstruct ZIP members in memory and use the production
parser. The parser selects ULTIMO; the test explicitly selects January-start YTD
DRE. ITR is not annualized and is not TTM or ranking evidence.

`python scripts/build_phase2_cvm_fixtures.py` recreates excerpts from the cache.
Run only for deliberate fixture review; upstream archives are mutable. Review
source checksums and values before accepting an update. Tests require no network.
CSV Git text conversion is disabled to preserve source bytes and hashes.

The integration tests use a synthetic market cap only to exercise assembly and
storage. Accounting PASS does not validate market prices, capital structure,
security identity, universe coverage or the independent release gate.
