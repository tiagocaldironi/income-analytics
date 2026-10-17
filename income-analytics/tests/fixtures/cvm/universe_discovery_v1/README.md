# Official universe discovery fixtures — V1

Reference: 2025-12-31. Manifest schema: `CVM_B3_UNIVERSE_RAW_EXCERPTS_V1`.

These fixtures derive from the already downloaded official CVM FCA/DFP and B3
COTAHIST annual archives. `manifest.json` records original and excerpt SHA-256
digests. They contain no manufactured financial values and no selected issuer list.

- FCA: complete original 2025 ZIP, including all general and security records.
- DFP: complete capital composition member; consolidated BPA/BPP/DRE rows for
  the approved component account codes, with `ORDEM_EXERC = ÚLTIMO`.
- COTAHIST: original records for securities discovered from FCA, in the inclusive
  2025-12-24 through 2025-12-31 window.

Omitted physical lines in excerpt members are replaced by blank lines, preserving
original source line numbers. CSV headers and retained records remain unchanged.
ZIP compression/container bytes differ for excerpts; archive and member digests
are recorded separately. Original data resides in `data/cvm` and `data/cotahist`.

To reconstruct: load full FCA, run `discover_candidates` at the reference, derive
tickers from its source records, retain the DFP account codes in the existing
`RULES` and the stated COTAHIST interval. Preserve blank padding when omitting rows.
The full FCA discovery defines membership; the five golden fixtures are used only
to test regression and provide already validated canonical capital evidence.

`tests/application/test_magic_formula_universe.py` checks hashes, source-driven
discovery, issuer grouping, all 18 required contract cases, fail-closed negatives,
and immutable read-back. No network or ranking execution is needed for discovery.
