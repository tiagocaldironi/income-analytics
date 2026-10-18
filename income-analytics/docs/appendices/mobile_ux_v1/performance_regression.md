# Performance regression

Mobile and desktop call the existing routes and APIs; no backend, schema, read model or payload code changed. The smoke run observed the expected portfolio routes once at initial load; changing `#minha-carteira` to `#minha-carteira/ativos` did not issue another dashboard or holdings request. Navigating to a different feature still activates that route's normal loader.

Server-side p95 baselines from the previous system-performance release remain historical reference values (wealth evolution 475 ms, wealth explanation 444 ms, portfolio performance 316 ms, comparison 104 ms). This UI-only change did not re-run that server-side p95 benchmark; no API logic changed, so no code path was added to those measurements. No material server-side regression is indicated by this change.
