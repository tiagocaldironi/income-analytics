# Income Analytics Mobile UX V1

**Implementation: complete. Spec release gate: FAIL** because the repository-wide Ruff check reports 133 findings in untouched files. All 871 Python tests passed; responsive browser checks passed. The existing desktop application, API, financial calculations and local-network-only deployment model remain in place. Physical-device validation was not available in this run.

The mobile shell adds a compact top bar, a five-destination bottom navigation, safe-area spacing and a “Mais áreas” sheet. Dashboard cards and holdings use a single-column hierarchy; holdings and monthly/annual performance data become labeled cards. The existing Magic Formula mobile-card variant remains in use. Forms and operation dialogs become bottom sheets. The desktop navigation and table presentation remain at desktop widths.

| Item | Result |
|---|---|
| P0 screens audited | 8 |
| P0: MOBILE_OK / ADAPT / REDESIGN | 1 / 5 / 2 |
| Shell, bottom navigation, safe areas and touch controls | PASS |
| Required widths 360×800, 390×844, 430×932 and landscape 844×390 | PASS |
| Unexpected page-level horizontal overflow | None in tested viewports and routes |
| Desktop 1440×900 | PASS |
| Desktop/mobile financial value sample | Identical for equity and first holding; amounts and identity redacted from saved evidence |
| Financial semantics, TWR, backend, schema, APIs | Unchanged |
| Duplicate request from switching Início ↔ Carteira anchor | None observed |
| LAN app | Existing server returned HTTP 200 and listens on `0.0.0.0:8000` |
| Physical device | NOT_RUN: no phone/browser remote-control surface was available |
| PWA | NOT_READY; not required for this phase |
| Full Python suite | PASS: 871 passed, 2 existing FastAPI deprecation warnings |
| Repository-wide Ruff | FAIL: 133 findings outside the files changed for this UX; no Python source was changed |

The automated browser run used local portfolio data and Chrome at desktop/mobile emulated viewports. It opened the “Mais” sheet and operation form, visited the P0 routes, compared displayed values at 390 px and 1440 px, and confirmed that the top navigation returns at desktop width. Switching between the dashboard and its holdings anchor generated zero additional portfolio requests. Saved screenshots and reports are anonymized because the remote repository is public. Screenshots and detailed test notes are in [the appendix](appendices/mobile_ux_v1/).

The monthly and annual return comparisons are now presented as cards on mobile. The chart itself remains full-width and benchmark calculations and selections continue to use the existing analytics response. No quote refresh, operation write or financial data mutation was triggered during validation.

PWA readiness is documented separately. This release does not add installability, offline behavior, external access, authentication or a new application frontend. The mobile experience is usable locally, but the specification's all-gates release status remains FAIL until the unrelated repository Ruff debt is cleared or formally waived.
