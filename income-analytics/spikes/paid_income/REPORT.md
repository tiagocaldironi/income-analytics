# Paid Income Provider Spike

## Run without `BRAPI_TOKEN`

Endpoint: `https://brapi.dev/api/quote/{ticker}?fundamental=true&dividends=true`

| Ticker | Asset type | HTTP | Result | Events (24m) |
|---|---|---:|---|---:|
| PETR4 | control | 200 | SUCCESS | 27 |
| TASA4 | stock | 401 | AUTH_REQUIRED | 0 |
| KLBN11 | unit | 401 | AUTH_REQUIRED | 0 |
| CMIG4 | stock | 401 | AUTH_REQUIRED | 0 |
| GGRC11 | FII | 401 | AUTH_REQUIRED | 0 |
| HSML11 | FII | 401 | AUTH_REQUIRED | 0 |

Observed semantic mapping: `rate → amount_per_unit`, `lastDatePrior → record_date`,
`paymentDate → payment_date`, `approvedOn → approval_date`, and `label → income_type`.
Only `paymentDate <= today` is counted as paid.

## Conclusion

**REJECTED for direct implementation on the free plan.** The authenticated run showed that
the free plan permits only 1d, 5d, 1mo and 3mo ranges. The requested 24-month range requires
the brapi Pro plan (reported by the provider as R$ 139,99/month). PETR4 is only a positive control.

An additional authenticated 3-month check returned `403 FEATURE_NOT_AVAILABLE` for TASA4,
KLBN11, CMIG4, GGRC11 and HSML11: the provider states that `Dividendos e JCP` require at least
the Startup plan (R$ 119,99/month). Therefore the free plan cannot be used even for a shorter
paid-income query of the mandatory coverage assets.

Recommended next step: configure `BRAPI_TOKEN` from either the free or paid account, rerun `python -m spikes.paid_income.runner`,
then cross-check three stock events and one FII event against B3, CVM or the issuer's RI.
No product-domain, UI, portfolio, migration or official database data was changed.
