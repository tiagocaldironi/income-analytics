# Finding Engine V2 Discovery

The current deterministic engine is `PortfolioDiagnosticEngine`. It returns an on-demand `PortfolioFinding` containing code, category, severity, title, description, evidence, and as-of date; it has no persistence, logical finding identity, trajectory, transition history, causal attribution, or structured subject.

Current rules are asset concentration, class/country/sector concentration, allocation-policy drift, incomplete valuation, incomplete risk coverage, and disproportionate risk contribution. `DiagnosticThresholds` owns hardcoded technical defaults: asset 25%, class 50%, country 70%, sector 45%, policy drift 10%, risk contribution multiple 2. Allocation drift only runs when a real allocation policy exists; the other thresholds are not user policy.

The `NOT_APPLICABLE` subject originates in diversification dimensions and must not be emitted as exposure concentration. It should become a data-quality observation only when classification coverage is inadequate.

The current API is `/portfolio/intelligence`; the frontend renders raw evidence as a metric dump. Historical as-of reconstruction exists, but no finding state is persisted, so trajectories cannot yet be responsibly inferred without a deterministic comparison snapshot.

Classification: policy drift `KEEP/REDESIGN`; concentration `KEEP/REDESIGN`; risk coverage `MOVE` to data quality; `NOT_APPLICABLE` concentration `FIX/REMOVE`.
