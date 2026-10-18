# Financial value reconciliation

The mobile and desktop views use the same `#equity`, holdings DOM, endpoints and response payload. At the tested local snapshot, both viewports displayed the same equity value and first holding identity. The exact value, security and quote date are intentionally omitted from this public report. The mobile card merely adds labels to existing table cells. Monthly/annual comparison rows preserve the same values and add presentation labels for mobile.

`FINANCIAL_VALUES_CHANGED=NO` · `FINANCIAL_SEMANTICS_CHANGED=NO` · `TWR_CHANGED=NO` · `MAGIC_FORMULA_CHANGED=NO` · `BACKEND_CHANGED=NO`.

No operation, quote update, import or write action was submitted while testing. The comparison was a UI-level equality check against the same rendered application data, not an independent recomputation of the finance engines. Screenshot evidence was anonymized before saving.
