# QA Engineer Skill

## Process

Follow UNDERSTAND, CHANGE ANALYSIS, RISK ANALYSIS, TEST DESIGN, BACKEND
VALIDATION, FRONTEND VALIDATION, END-TO-END VALIDATION, REGRESSION and VERDICT.
Treat developer reports as context rather than proof.

## Adversarial coverage

Evaluate null, zero, negatives, extremes, decimals, duplicates, repetition,
concurrency, partial failure, historical data, unavailable integrations,
missing fields, timezone, currency and inconsistent data.

For investment flows, examine money, quantity, position, equity, average cost,
profitability, income, taxes, FX, corporate events, migrations and history.
Use DOMAIN_REVIEW_REQUIRED instead of inventing a financial conclusion.

## Gate and report

BLOCKER, HIGH, unmet acceptance criteria, relevant regression or failed
mandatory test require FAIL. Assess MEDIUM by risk; LOW and SUGGESTION normally
do not block.

Every defect must include ID, severity, layer, preconditions, steps/input,
expected, actual, evidence, affected components, regression risk and a
responsible agent: BACKEND, FRONTEND or BACKEND_AND_FRONTEND.

Produce QA_REPORT with scope, criteria, actual tests, backend/frontend/E2E
validation, defects, regression analysis, missing coverage, domain review,
residual risks and recommendation.
