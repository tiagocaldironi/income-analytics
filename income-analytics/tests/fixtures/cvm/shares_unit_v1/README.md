# Historical share unit evidence V1

The frozen sample contains 25 previously unresolved issuers and five canonical
controls. Selection uses maximum coverage of source-derived strata, with UUID
tie-breaking; no issuer name or ticker supplies membership. Strata cover economic
sector, total-assets size terciles, security classes, treasury presence, multiple
securities and raw digit patterns. Raw magnitude affects sampling only, never unit
resolution. `sample.json` preserves the exact CSV capital rows and document links.

Each `*-evidence.zip` is a small, explicitly labelled projection of an original
official CVM DFP package. Identity/date/version/scale/capital XML fields preserve
their source values. Unrelated XML content is omitted; no financial value is
manufactured. Metadata distinguishes projected XML hashes from original XML hashes
and the downloaded archive/PDF hashes. The unmodified descriptor XML and complete
extracted capital-page text are included. These are raw-source test fixtures, not
new canonical golden issuers or financial snapshots.

`manifest.json` records URLs and hashes, plus hashes of the unchanged ranking engine
and canonical contract. `meta_dfp_cia_aberta_txt.zip` is the official CVM metadata
archive downloaded from its DFP META directory. Its capital fields have integer
storage precision but no quantity-unit column or economic scale declaration.

The original document adds `DadosDFP/EscalaQtdAcoes`; the descriptor repeats it as
`CodigoEscalaQuantidade`. Code 1 corresponds to the PDF's `Unidades`, and code 2 to
`Mil`, as verified separately in all sample documents. Runtime policy still requires
both XML fields and the PDF label on the exact same historical document; it does
not assume a dataset default. PDF class quantities must match XML, then XML must
match the CSV issuer/date/version/quantities. Unknown/conflicting cases fail closed.

Reconstruction tools: `scripts/sample_historical_shares_units.py`,
`scripts/fetch_historical_shares_documents.py` and the audit helper
`tmp/shares-unit-phase2/build_fixtures.py`. Acquisition requires pypdf; unit policy,
fixture parsing and tests use the project's standard environment.
