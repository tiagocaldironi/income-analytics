# Petrobras: official RAW excerpts, V1

These are **test excerpts**, not complete CVM/B3 distributions. They contain
unaltered source records from the local official archives identified by SHA-256
in `manifest.json`. No amounts, prices, shares, or expected metrics were invented.

- DFP: all Petrobras records dated 2025-12-31 in consolidated BPA/BPP/DRE,
  including prior-period rows, and the capital-composition record. Original
  headers, columns, decimal representation, encoding, and row bytes are retained.
- FCA: original PETR3/PETR4 security records, reference 2025-01-01, form 147760.
- COTAHIST: original PETR3/PETR4 records in the seven-day window ending
  2025-12-31. Unrelated physical lines are replaced by blank lines; the original
  line numbers remain intact. The closing records are lines 1692376 and 1692377.
  ISINs come from columns 231–242 of these B3 records; the FCA CSV has no ISIN column.

The manifest records the SHA-256 of each original archive, each CVM member and
excerpt, each excerpt ZIP, and every retained B3 record at its original line.
Tests validate these checksums and execute the same parsers, evidence builders,
serializer, locator verifier, snapshot writer, dimensional QA, and eligibility
policy used for the real recovery. Production uses the full archives under
`data/cvm` and `data/cotahist`, never these excerpts.

Approved capital units are `UNIT`, multiplier `1`; this is the previously
approved Petrobras mapping, not an inference from the magnitude of quantities.
The known acceptance anchors are assertions after evidence construction.

No database or persisted expected snapshot is required to run these tests.
The tests migrate a clean temporary database to revision 0016, and separately
exercise recovery alongside four existing canonical issuer artifacts.
