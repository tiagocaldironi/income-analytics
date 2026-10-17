# Official historical identity recovery fixture V1

Source issuer and capital/accounting evidence come from the frozen universe snapshot
`6d418683-6c09-4cfd-a67b-a4cc54718ddd`. The offer notice is an unchanged B3-hosted
PDF dated 2021-01-22. Its cover identifies CNPJ, ticker and ISIN; the signed date
is on page 44. The current directory response corroborates identity only and does
not independently authorize historical recovery.

`cotahist-record.txt` is the unchanged source line selected from the pinned official
annual archive. It is a fixture, not a manually supplied price. `manifest.json`
contains original URLs, retrieval timestamps, source archive/line and SHA-256 hashes.
No network is required for the regression test. PDF extraction and independent
read-back use pypdf and pdfplumber respectively, with visual review of both pages.

This fixture proves source identity and historical price for a preview recovery.
It does not create canonical formal QA or production ranking authorization.
