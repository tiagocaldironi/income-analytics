# PR 5 — Global executable contribution allocation

The previous planner reserved monetary suggestions for classes without a complete asset policy. After rounding purchases, only the unreserved remainder could compete. This could exclude an affordable purchase elsewhere even when it improved whole-portfolio adherence. Missing policy still prevents purchases in that class; its monetary suggestion no longer locks cash away from other eligible assets.

## Planning and objective

The planner starts with no purchases and evaluates every eligible instrument against the entire projected portfolio. It reuses the official class distance calculation and the existing validation of quotes, currencies, quantities, minimums and supplied costs. Candidate quantities include executable minimums, affordable limits and target crossings, including dilution of other classes.

The deterministic lexical objective minimizes global class total-variation distance, then configured asset distance, then maximizes invested principal, then minimizes costs. Sorted ticker/quantity signatures break ties. Neither presentation order nor an initial monetary recommendation determines priority.

A bounded search explores bundles of up to three purchases, retaining twelve states per level, with a 20,000-candidate ceiling and an iteration ceiling. Hypothetical intermediate nodes may worsen distance; they are never accepted individually. Each accepted purchase bundle must improve the lexical objective without worsening global class distance. This handles balanced indivisible lots without claiming a general discrete global optimum.

For example, a synthetic portfolio with values 60/40 and targets 50/50, purchase prices 40/20 and budget 100 has a greedy trap: buying one unit of the second asset reaches alignment but leaves 80. A bundle of one first-asset unit and three second-asset units invests 100 while preserving alignment. Regression coverage compares these alternatives.

## Diagnostics and residual cash

Additive diagnostics expose initial/final class and asset distances, accepted bundle traces, evaluated candidates, discarded minimum purchases, search limits and stopping reason. Missing asset policies retain their reference monetary amounts for explanation, without reserving cash. Insufficient overall valuation remains blocked.

Residual explanations distinguish minimum purchase cost, missing/stale quotations or FX, missing asset policies, trading restrictions and strategy limits. A search limit explicitly means that inevitability has not been established. Broker fees not supplied by the user remain unknown; quote references do not guarantee execution.

## Verification

- 103 focused Python tests cover authorization, executable allocation, global allocation, the official contribution allocator/projector and frontend module contracts.
- Five frontend suites cover executable simulation, simulation experience, portfolio rendering/loading and XSS characterization.
- Cases include multiple classes, re-evaluation, input-order independence, integer B3 lots, supported fractions, budget bounds, unavoidable remainder, stale/missing prices, objective monotonicity, deterministic termination, greedy traps and balanced three-class bundles.
- The real reported scenario was reproduced from a private read-only SQLite snapshot with frozen quotations before changing the planner. An independent enumeration of 38 feasible integer plans confirmed the corrected result for that snapshot. The detailed before/after comparison and holdings are retained privately, outside Git.

No certified domain/performance implementation, ledger, real position or database schema is modified. The interface structure is preserved; explanatory text follows the returned diagnostics. Production is unchanged. Merge and deployment require a subsequent instruction.
