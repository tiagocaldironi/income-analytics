// Centralized HTTP client for the local portfolio API.

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`/api${path}`, {
      cache: "no-store",
      ...options,
      signal: options.signal || controller.signal,
    });
    const parseStarted = performance.now();
    const body = await response.json().catch(() => ({}));
    performance.measure("income:json-parse", {
      start: parseStarted,
      end: performance.now(),
      detail: { path },
    });
    if (!response.ok) {
      const detail = Array.isArray(body.detail)
        ? body.detail.map(item => {
          const field = Array.isArray(item.loc) ? item.loc.at(-1) : "";
          return (field ? field + ": " : "") + (item.msg || item.message || "Dado inválido.");
        }).join(" ")
        : body.detail;
      throw new Error(detail || "Não foi possível concluir a operação.");
    }
    return body;
  } finally {
    window.clearTimeout(timeout);
  }
}

export const portfolioApi = {
  tools: () => request("/tools"),
  magicFormulaStocks: (filters = {}) => {
    const query = new URLSearchParams({
      q: filters.query || filters.q || "",
      exclude_retail: String(Boolean(filters.excludeRetail)),
      exclude_aviation: String(Boolean(filters.excludeAviation)),
      page: String(filters.page || 1),
      page_size: String(filters.pageSize || 25),
    });
    return request("/tools/magic-formula/stocks?" + query.toString());
  },
  magicFormulaStockDetail: (companyId, snapshotId) => request(
    "/tools/magic-formula/stocks/" + encodeURIComponent(companyId)
    + (snapshotId ? "?snapshot_id=" + encodeURIComponent(snapshotId) : ""),
  ),
  magicFormulaFiis: () => request("/tools/magic-formula/fiis"),
  automaticPriceForClass: (ticker, date, assetClass) => request(
    "/market-prices/" + encodeURIComponent(ticker) + "/automatic?effective_date="
    + encodeURIComponent(date) + "&asset_class=" + encodeURIComponent(assetClass),
  ),
  assetSearch: (query, assetClass = "") => request(
    `/assets/search?q=${encodeURIComponent(query)}`
    + `&asset_class=${encodeURIComponent(assetClass)}`,
  ),
  createAsset: payload => request("/assets", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  createFixedIncome: payload => request("/assets/fixed-income", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  createPensionPlan: payload => request("/assets/pension-plans", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  associatePensionVehicle: (ticker, payload) => request(`/pensions/${ticker}/vehicle`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  createRealEstate: payload => request("/assets/real-estate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  recurringRules: () => request("/recurring-rules"),
  createRecurringRule: payload => request("/recurring-rules", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  updateRecurringRule: (id, payload) => request(`/recurring-rules/${encodeURIComponent(id)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  closeRecurringRule: id => request(`/recurring-rules/${encodeURIComponent(id)}/close`, { method: "POST" }),
  deleteRecurringRule: id => request(`/recurring-rules/${encodeURIComponent(id)}`, { method: "DELETE" }),
  executeRecurringRules: through => request(`/recurring-rules/execute?through=${encodeURIComponent(through)}`, { method: "POST" }),
  portfolio: asOf => request(`/portfolio${asOf ? `?as_of=${encodeURIComponent(asOf)}` : ""}`),
  dashboard: () => request("/portfolio/dashboard"),
  holdings: asOf => request(`/portfolio/holdings${asOf ? `?as_of=${encodeURIComponent(asOf)}` : ""}`),
  assetTransactions: (assetId, params = {}) => {
    const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value !== "" && value !== null && value !== undefined));
    return request(`/portfolio/assets/${encodeURIComponent(assetId)}/transactions${query.size ? `?${query}` : ""}`);
  },
  operations: () => request("/operations"),
  operationsHistory: params => request(`/operations/history?${new URLSearchParams(Object.entries(params).filter(([, value]) => value !== "" && value !== null && value !== undefined)).toString()}`),
  deleteOperation: id => request(`/operations/${encodeURIComponent(id)}`, { method: "DELETE" }),
  history: (periodMonths = 12, assetClass = "") => request(`/portfolio/history?period_months=${periodMonths}${assetClass ? `&asset_class=${encodeURIComponent(assetClass)}` : ""}`),
  historyRange: (start, end) => request(`/portfolio/history?period_months=0&start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`),
  allocation: asOf => request(`/portfolio/allocation${asOf ? `?as_of=${encodeURIComponent(asOf)}` : ""}`),
  classAllocation: asOf => request(`/portfolio/class-allocation${asOf ? `?as_of=${encodeURIComponent(asOf)}` : ""}`),
  allocationAnalysis: asOf => request(`/portfolio/allocation-analysis${asOf ? `?as_of=${encodeURIComponent(asOf)}` : ""}`),
  intelligence: asOf => request(`/portfolio/intelligence${asOf ? `?as_of=${encodeURIComponent(asOf)}` : ""}`),
  diversification: () => request("/portfolio/diversification"),
  createTrade: payload => request("/trades", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  previewIrpfBrazilianStocks: workbook_base64 => request("/imports/irpf/brazilian-stocks/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workbook_base64 }) }),
  importIrpfBrazilianStocks: workbook_base64 => request("/imports/irpf/brazilian-stocks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workbook_base64 }) }),
  previewB3Import: payload => request("/imports/b3/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  applyB3Import: batchId => request(`/imports/b3/${encodeURIComponent(batchId)}/apply`, { method: "POST" }),
  b3ImportHistory: (offset = 0, pageSize = 20) => request(`/imports/b3/history?offset=${offset}&page_size=${pageSize}`),
  jcp: payload => request("/jcp", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  dividend: payload => request("/dividends", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  externalFlow: payload => request("/external-flows", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  updatePrice: (ticker, payload) => request(`/market-prices/${encodeURIComponent(ticker)}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  refreshPrices: () => request("/market-prices/refresh", { method: "POST" }),
  marketPriceRefreshRuns: limit => request("/market-prices/refresh-runs?limit=" + encodeURIComponent(limit)),
  automaticPrice: (ticker, date) => request(`/market-prices/${encodeURIComponent(ticker)}/automatic?effective_date=${date}`),
  resetAllData: () => request("/data/reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ confirmation: "EXCLUIR" }) }),
  performance: (start, end) => request(`/portfolio/performance?start_date=${start}&end_date=${end}`),
  wealthExplanation: (start, end) => request(`/analytics/wealth-explanation?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`),
  wealthEvolution: (start, end) => request(`/analytics/wealth-evolution?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}`),
  benchmarkComparison: (name, start, end) => request(`/portfolio/benchmark-comparison?name=${encodeURIComponent(name)}&start_date=${start}&end_date=${end}`),
  performanceComparison: (start, end, assetClass = "") => request(`/analytics/performance-comparison?start_date=${encodeURIComponent(start)}&end_date=${encodeURIComponent(end)}${assetClass ? `&asset_class=${encodeURIComponent(assetClass)}` : ""}`),
  risk: (start, end) => request(`/portfolio/risk?start_date=${start}&end_date=${end}`),
  rebalancing: () => request("/portfolio/rebalancing"),
  contribution: amount => request("/portfolio/rebalancing/contribution-only", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ amount }) }),
  simulateContribution: payload => request("/portfolio/simulation/contribution", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  assetRebalancing: payload => request("/portfolio/rebalancing/assets", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  benchmark: (name, payload) => request(`/benchmarks/${name}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  refreshBenchmark: (name, start, end) => request(`/benchmarks/${encodeURIComponent(name)}/refresh?start_date=${start}&end_date=${end}`, { method: "POST" }),
  benchmarkObservations: name => request(`/benchmarks/${encodeURIComponent(name)}`),
  configuration: () => request("/portfolio/configuration"),
  updateConfiguration: payload => request("/portfolio/configuration", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  refreshFx: (base, quote, date) => request(`/fx/${encodeURIComponent(base)}/${encodeURIComponent(quote)}/refresh?effective_date=${date}`, { method: "POST" }),
  dataSources: () => request("/data-sources"),
  paidIncomeSettings: () => request("/settings/paid-income"),
  updatePaidIncomeSettings: payload => request("/settings/paid-income", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  testPaidIncome: () => request("/settings/paid-income/test", { method: "POST" }),
  syncPaidIncome: () => request("/settings/paid-income/sync", { method: "POST" }),
  allocationPolicy: targets => request("/allocation-policy", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ targets }) }),
  assetAllocationPolicy: targets => request("/asset-allocation-policy", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ targets }) }),
};
