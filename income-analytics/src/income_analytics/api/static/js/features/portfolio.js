import { invalidatePortfolioGuidance, setupContextualOnboarding } from "./portfolio-guidance-v2.js";
import { setupPortfolioView, updatePortfolioView } from "./portfolio-view-v2.js";
import { portfolioApi } from "../api.js";
import { financialConcepts } from "../shared/financial-concepts.js";
import { emptyState, errorState, loadingState, money, percentage, table } from "../shared/ui.js";
import { loadECharts, chartTheme } from "../shared/charts.js";

let currentHoldings = null;
let holdingsClass = "";
let holdingsQuery = "";
let holdingsSort = "name";
let holdingsWallet = null;
const holdingsPreferences = new Map();
const holdingsOpenGroups = new Map();
const holdingsSkeleton = '<div class="holdings-skeleton" role="status" aria-label="Carregando investimentos"><span></span><span></span><span></span></div>';
function normalizeHoldingText(value) { return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR"); }
function selectHoldingAssets(group) {
  const query = normalizeHoldingText(holdingsQuery.trim());
  return assetsForDisplay(group).filter(asset => !query || normalizeHoldingText([asset.name, asset.ticker, asset.display_name].join(" ")).includes(query)).sort((a,b) => {
    if (holdingsSort !== "name") {
      const currency = String(a.currency_code || "BRL").localeCompare(String(b.currency_code || "BRL"));
      if (currency) return currency;
      const av = a.market_value, bv = b.market_value;
      if (av === null || av === undefined) return bv === null || bv === undefined ? 0 : 1;
      if (bv === null || bv === undefined) return -1;
      const delta = Number(av) - Number(bv);
      if (delta) return holdingsSort === "value-desc" ? -delta : delta;
    }
    return String(a.display_name || a.name || a.ticker).localeCompare(String(b.display_name || b.name || b.ticker), "pt-BR");
  });
}
function saveHoldingsPreferences() {
  holdingsPreferences.set(holdingsWallet, {class:holdingsClass,query:holdingsQuery,sort:holdingsSort});
}
function renderHoldingsCategories() {
  const target = document.querySelector("#holdings-categories");
  if (!target || !currentHoldings) return;
  const groups = currentHoldings.classes.filter(group => assetsForDisplay(group).length);
  target.innerHTML = `<button type="button" data-holdings-class="" aria-pressed="${!holdingsClass}">Todos os investimentos</button>` + groups.map(group => `<button type="button" data-holdings-class="${escapeHtml(group.asset_class)}" aria-pressed="${holdingsClass===group.asset_class}"><span>${escapeHtml(group.label)}</span><small>${assetsForDisplay(group).length} · ${group.weight == null ? "Participação indisponível" : percentage(group.weight * 100)}</small></button>`).join("");
}

let portfolioLoadSequence = 0;
let equityChart = null;
let equityChartResizeObserver = null;
let equityChartRequestId = 0;
let openAssetMenu = null;
let assetTransactionsTrigger = null;
let assetTransactionsRequestId = 0;
let portfolioInteractionsBound = false;
let groupDistributionTrigger = null;
let groupDistributionChart = null;
let portfolioFiltersBound = false;
let incomeChartInstances = [];
let incomeRenderSequence = 0;
let portfolioPerformanceChart = null;
let portfolioPerformanceResizeObserver = null;
let portfolioPerformanceRequestId = 0;
let portfolioPerformancePeriod = "MAX";
const portfolioBenchmarkSelection = new Set(["portfolio", "CDI", "IBOV", "IFIX"]);

export async function loadPortfolio(asOf = "", { refreshAttention = true } = {}) {
  const sequence = ++portfolioLoadSequence;
  invalidatePortfolioGuidance();
  const wallet = typeof localStorage === "undefined" ? null : localStorage.getItem("income.activePortfolioId");
  if (wallet !== holdingsWallet) {
    saveHoldingsPreferences(); holdingsWallet = wallet;
    const saved = holdingsPreferences.get(wallet);
    holdingsClass = saved?.class || ""; holdingsQuery = saved?.query || ""; holdingsSort = saved?.sort || "name";
    holdingsOpenGroups.clear();
  }
  currentHoldings = null;
  if (openAssetMenu) { openAssetMenu.hidden=true;openAssetMenu=null; }
  const policy = document.querySelector("#allocation-policy-dialog");
  if (policy?.open) policy.close();
  ++assetTransactionsRequestId;
  const transactions = document.querySelector("#asset-transactions-modal");
  if (transactions?.open) transactions.close();
  const distribution = document.querySelector("#group-distribution-modal");
  if (distribution?.open) distribution.close();
  const categories = document.querySelector("#holdings-categories");
  if (categories) categories.textContent = "";
  const count = document.querySelector("#holdings-count");
  if (count) count.textContent = "";
  ++portfolioPerformanceRequestId;
  ++equityChartRequestId;
  const metricIds = ["equity", "home-return", "income", "net-invested"];
  metricIds.forEach(id => { const node = document.querySelector(`#${id}`); if (node) node.textContent = "Carregando…"; });
  const insight = document.querySelector("#portfolio-insight");
  if (insight) { insight.hidden = true; insight.textContent = ""; }
  const containers = ["#positions", "#understand-history", "#allocation", "#class-allocation", "#portfolio-evolution", "#portfolio-performance-chart", "#monthly-income-chart"];
  containers.forEach(selector => {
    const container = document.querySelector(selector);
    if (container) container.innerHTML = selector === "#positions" ? holdingsSkeleton : loadingState;
  });
  try {
    // First render is one fast read-model request. Financial consolidation runs
    // only when the snapshot is rebuilt after a write.
    const dashboard = await portfolioApi.dashboard();
    if (sequence !== portfolioLoadSequence) return;
    const { portfolio, performance, history, allocation, class_allocation: classes, holdings } = dashboard;
    renderPortfolio(portfolio, holdings, performance);
    updatePortfolioView(dashboard);
    renderHistory(history, holdings.base_currency || portfolio.base_currency || "BRL");
    renderAllocation(allocation);
    renderClasses(holdings, classes);
    loadPortfolioPerformanceChart();
    portfolioApi.operations().then(data => { if (sequence === portfolioLoadSequence) renderMonthlyIncome(data); }).catch(error => {
      if (sequence !== portfolioLoadSequence) return;
      console.error("Falha ao carregar rendimentos mensais", error);
      const target = document.querySelector("#monthly-income-chart");
      if (target) target.innerHTML = errorState("Não foi possível carregar os rendimentos mensais.");
    });
    if (refreshAttention) document.dispatchEvent(new Event("portfolio:intelligence-refresh"));
  } catch (error) {
    if (sequence !== portfolioLoadSequence) return;
    console.error("Falha ao renderizar Minha Carteira", error);
    metricIds.forEach(id => { const node = document.querySelector(`#${id}`); if (node) node.textContent = "Indisponível"; });
    containers.forEach(selector => {
      const container = document.querySelector(selector);
      if (container) container.innerHTML = selector === "#positions" ? '<div class="holdings-state" role="alert"><p>Não foi possível carregar seus investimentos.</p><button type="button" class="income-button secondary" data-holdings-retry>Tentar novamente</button></div>' : errorState(error.message);
    });
  }
}

export function bindPortfolioFilters() {
  if (portfolioFiltersBound) return;
  portfolioFiltersBound = true;
  setupContextualOnboarding();
  setupPortfolioView(() => {
    [equityChart, portfolioPerformanceChart, ...incomeChartInstances].forEach(chart => {
      if (!chart || chart.isDisposed()) return;
      const colors = chartTheme();
      chart.setOption({textStyle:{color:colors.text},xAxis:{axisLabel:{color:colors.muted},axisLine:{lineStyle:{color:colors.border}}},yAxis:{axisLabel:{color:colors.muted},splitLine:{lineStyle:{color:colors.border}}},tooltip:{backgroundColor:colors.surface,textStyle:{color:colors.text},borderColor:colors.border}});
      chart.resize();
    });
  });
  document.addEventListener("input", event => {
    if (event.target.id !== "holdings-search" || !currentHoldings) return;
    holdingsQuery = event.target.value; saveHoldingsPreferences(); renderHoldings();
  });
  document.addEventListener("toggle", event => {
    if (event.target.matches?.("#positions > details[data-holdings-group]")) holdingsOpenGroups.set(event.target.dataset.holdingsGroup,event.target.open);
  }, true);
  document.addEventListener("change", async event => {
    if (event.target.id === "holdings-sort" && currentHoldings) { holdingsSort=event.target.value; saveHoldingsPreferences(); renderHoldings(); return; }
    if (event.target.matches("#portfolio-performance-period")) {
      portfolioPerformancePeriod = event.target.value;
      loadPortfolioPerformanceChart();
      return;
    }
    if (event.target.matches("[data-portfolio-benchmark]")) {
      const code = event.target.dataset.portfolioBenchmark;
      if (event.target.checked) portfolioBenchmarkSelection.add(code);
      else portfolioBenchmarkSelection.delete(code);
      updatePortfolioPerformanceLegend();
      return;
    }
    if (!event.target.matches("#portfolio-history-period, #portfolio-history-class")) return;
    const period = document.querySelector("#portfolio-history-period")?.value || "12";
    const assetClass = document.querySelector("#portfolio-history-class")?.value || "";
    const chart = document.querySelector("#portfolio-evolution");
    chart.innerHTML = loadingState;
    try { renderHistory(await portfolioApi.history(period, assetClass), currentHoldings?.base_currency || "BRL"); }
    catch (error) { chart.innerHTML = errorState(error.message); }
  });
  document.addEventListener("click", event => {
    const category = event.target.closest("[data-holdings-class]");
    if (category && currentHoldings) {
      holdingsClass = category.dataset.holdingsClass; saveHoldingsPreferences(); renderHoldingsCategories(); renderHoldings();
      [...document.querySelectorAll("[data-holdings-class]")].find(node => node.dataset.holdingsClass === holdingsClass)?.focus();
    }
    if (event.target.closest("[data-holdings-clear]") && currentHoldings) {
      holdingsClass="";holdingsQuery="";holdingsSort="name";saveHoldingsPreferences();
      document.querySelector("#holdings-search").value="";document.querySelector("#holdings-sort").value="name";
      renderHoldingsCategories();renderHoldings();document.querySelector("#holdings-search").focus();
    }
    if (event.target.closest("[data-holdings-retry]")) loadPortfolio();
    const details = event.target.closest("[data-holding-details]");
    if (details) { const row=details.closest("tr"); const expanded=details.getAttribute("aria-expanded")!=="true";row.classList.toggle("holding-expanded",expanded);details.setAttribute("aria-expanded",String(expanded));details.textContent=expanded?"Menos detalhes":"Mais detalhes"; }
    if (event.target.closest("#portfolio-new-operation, #holdings-first-operation")) window.dispatchEvent(new Event("income:open-operation"));
    if (event.target.closest("#open-allocation-policy")) openAllocationPolicy();
    const groupChart = event.target.closest("[data-group-distribution]");
    if (groupChart) {
      event.preventDefault();
      event.stopPropagation();
      openGroupDistribution(groupChart.dataset.groupId, groupChart);
    }
  });
  bindPortfolioInteractions();
}

const portfolioBenchmarkSeries = [
  { code: "portfolio", label: "Minha carteira (TWR)", color: "#829cf3", type: "TWR" },
  { code: "CDI", label: "CDI", color: "#ffbd45", type: "Retorno total acumulado" },
  { code: "IBOV", label: "Ibovespa", color: "#5b9cff", type: "Índice de preços" },
  { code: "IFIX", label: "IFIX", color: "#9e4a18", type: "Índice de preços" },
  { code: "IVVB11", label: "IVVB11 · proxy em BRL", color: "#9b59b6", type: "Preço de ETF em BRL" },
  { code: "SP500", label: "S&P 500 em BRL", color: "#c9c9c9", type: "Indisponível" },
];

function localDateString(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function portfolioComparisonRange(period) {
  const end = new Date();
  const endDate = localDateString(end);
  if (period === "MAX") return { startDate: "", endDate };
  const start = new Date(end.getFullYear(), end.getMonth(), end.getDate());
  if (period === "YTD") start.setMonth(0, 1);
  else {
    const day = start.getDate();
    start.setDate(1);
    start.setMonth(start.getMonth() - Number(period));
    start.setDate(Math.min(day, new Date(start.getFullYear(), start.getMonth() + 1, 0).getDate()));
  }
  return { startDate: localDateString(start), endDate };
}

function portfolioPerformanceControls(data, available) {
  const periodOptions = [["1", "1M"], ["3", "3M"], ["6", "6M"], ["12", "12M"], ["YTD", "YTD"], ["MAX", "Máximo"]]
    .map(([value, label]) => `<option value="${value}"${portfolioPerformancePeriod === value ? " selected" : ""}>${label}</option>`).join("");
  const codes = new Set(data.benchmarks.map(item => item.code));
  const choices = portfolioBenchmarkSeries.map(item => {
    const exists = item.code === "portfolio" ? available : codes.has(item.code) && data.benchmarks.some(row => row.code === item.code && row.return !== null && row.status !== "UNAVAILABLE");
    const selected = portfolioBenchmarkSelection.has(item.code);
    return `<label${exists ? "" : ' aria-disabled="true"'}><input type="checkbox" data-portfolio-benchmark="${item.code}"${selected && exists ? " checked" : ""}${exists ? "" : " disabled"}><i style="background:${item.color}"></i>${item.label}</label>`;
  }).join("");
  return `<div class="portfolio-performance-controls"><label>Período<select id="portfolio-performance-period">${periodOptions}</select></label><div class="portfolio-benchmark-options" aria-label="Séries exibidas">${choices}</div></div>`;
}

async function loadPortfolioPerformanceChart() {
  const target = document.querySelector("#portfolio-performance-chart");
  if (!target) return;
  const requestId = ++portfolioPerformanceRequestId;
  target.innerHTML = loadingState;
  try {
    const { startDate, endDate } = portfolioComparisonRange(portfolioPerformancePeriod);
    const data = await portfolioApi.performanceComparison(startDate, endDate);
    if (requestId !== portfolioPerformanceRequestId || !target.isConnected) return;
    renderPortfolioPerformanceChart(data, requestId);
  } catch (error) {
    if (requestId === portfolioPerformanceRequestId && target.isConnected) target.innerHTML = errorState("Não foi possível carregar a comparação de rentabilidade.");
    console.error("Falha ao carregar comparação de rentabilidade", error);
  }
}

async function renderPortfolioPerformanceChart(data, requestId) {
  const target = document.querySelector("#portfolio-performance-chart");
  if (!target) return;
  const available = data.portfolio.return !== null && ["AVAILABLE", "PARTIAL"].includes(data.portfolio.status);
  const rows = data.series || [];
  if (!rows.length) {
    target.innerHTML = emptyState("Série indisponível", "Não há observações históricas suficientes no período selecionado.");
    return;
  }
  const controls = portfolioPerformanceControls(data, available);
  const range = data.period || {};
  const baseDate = range.start ? new Date(`${range.start}T00:00:00`).toLocaleDateString("pt-BR") : "data inicial disponível";
  const note = `Base comparável: ${baseDate}. CDI: retorno acumulado; Ibovespa e IFIX: índices de preços; IVVB11: preço de mercado do ETF em BRL, usado apenas como proxy. S&P 500 em BRL indisponível: ainda não há série histórica integrada com câmbio.`;
  const hasBenchmarkData = data.benchmarks.some(item => item.return !== null && item.return !== undefined && item.status !== "UNAVAILABLE");
  if (!available && !hasBenchmarkData) {
    target.innerHTML = `${controls}${emptyState("Comparação indisponível", "Não há TWR validado nem séries de índices suficientes no período selecionado.")}<p class="portfolio-chart-note">${note}</p>`;
    return;
  }
  target.innerHTML = `${controls}<div id="portfolio-performance-echarts" class="portfolio-performance-chart" aria-label="Rentabilidade acumulada comparada"></div><p class="portfolio-chart-note">${note}</p>${!available ? `<p class="coverage" role="status">TWR da carteira indisponível para este período. As séries de mercado disponíveis são exibidas separadamente, sem estimar a rentabilidade da carteira.</p>` : data.portfolio.status === "PARTIAL" ? `<p class="coverage" role="status">TWR parcial, com cobertura de ${percentage(Number(data.portfolio.coverage) * 100)} do patrimônio.</p>` : ""}`;
  const chartTarget = target.querySelector("#portfolio-performance-echarts");
  const echarts = await loadECharts();
  if (!chartTarget?.isConnected || requestId !== portfolioPerformanceRequestId) return;
  portfolioPerformanceResizeObserver?.disconnect();
  if (portfolioPerformanceChart && !portfolioPerformanceChart.isDisposed()) portfolioPerformanceChart.dispose();
  portfolioPerformanceChart = echarts.init(chartTarget, null, { renderer: "svg" });
  const series = portfolioBenchmarkSeries.slice(0, 5).map(item => ({
    name: item.code === "portfolio" ? "Minha carteira (TWR)" : item.label,
    type: "line",
    smooth: false,
    connectNulls: false,
    showSymbol: false,
    data: rows.map(point => item.code === "portfolio" ? (available ? point.portfolio : null) : point[item.code.toLowerCase()]),
    lineStyle: { color: item.color, width: 2 },
    itemStyle: { color: item.color },
  }));
  const option = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis", valueFormatter: amount => amount === null || amount === undefined ? "Indisponível" : percentage(Number(amount) * 100) },
    legend: { show: false, selectedMode: true },
    grid: { left: 58, right: 18, top: 40, bottom: 34 },
    xAxis: { type: "category", data: rows.map(point => point.date), axisLabel: { color: chartTheme().muted }, axisLine: { lineStyle: { color: chartTheme().border } } },
    yAxis: { type: "value", axisLabel: { color: chartTheme().muted, formatter: value => `${(Number(value) * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%` }, splitLine: { lineStyle: { color: chartTheme().border } } },
    series,
  };
  portfolioPerformanceChart.setOption(option, true);
  portfolioBenchmarkSeries.slice(0, 5).forEach(item => {
    const input = target.querySelector(`[data-portfolio-benchmark="${item.code}"]`);
    if (!input) return;
    portfolioPerformanceChart.dispatchAction({ type: input.checked ? "legendSelect" : "legendUnSelect", name: item.code === "portfolio" ? "Minha carteira (TWR)" : item.label });
  });
  portfolioPerformanceResizeObserver = new ResizeObserver(() => portfolioPerformanceChart?.resize());
  portfolioPerformanceResizeObserver.observe(chartTarget);
  portfolioPerformanceChart.resize();
}

function updatePortfolioPerformanceLegend() {
  if (!portfolioPerformanceChart || portfolioPerformanceChart.isDisposed()) return;
  portfolioBenchmarkSeries.slice(0, 5).forEach(item => {
    const name = item.code === "portfolio" ? "Minha carteira (TWR)" : item.label;
    portfolioPerformanceChart.dispatchAction({ type: portfolioBenchmarkSelection.has(item.code) ? "legendSelect" : "legendUnSelect", name });
  });
}

function bindPortfolioInteractions() {
  if (portfolioInteractionsBound) return;
  portfolioInteractionsBound = true;
  document.addEventListener("click", event => {
    const trigger = event.target.closest("[data-asset-options]");
    if (trigger) {
      toggleAssetMenu(trigger);
      return;
    }
    const operationAction = event.target.closest("[data-open-operation]");
    if (operationAction) {
      closeAssetMenu();
      window.dispatchEvent(new CustomEvent("income:open-operation", { detail: {
        eventType: operationAction.dataset.operationType,
        assetClass: operationAction.dataset.operationClass,
        ticker: operationAction.dataset.operationTicker,
        name: operationAction.dataset.operationName,
        country: operationAction.dataset.operationCountry,
        currencyCode: operationAction.dataset.operationCurrency,
        sector: operationAction.dataset.operationSector,
      }}));
      return;
    }
    const transactionAction = event.target.closest("[data-asset-transactions]");
    if (transactionAction) {
      const menu = transactionAction.closest(".asset-context-menu");
      closeAssetMenu();
      openAssetTransactions(transactionAction.dataset.assetId, transactionAction.dataset.assetTitle, menu?.previousElementSibling);
      return;
    }
    if (openAssetMenu && !openAssetMenu.contains(event.target)) closeAssetMenu();
  });
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    if (openAssetMenu) {
      event.preventDefault();
      closeAssetMenu(true);
    }
  });
}

function toggleAssetMenu(trigger) {
  const menu = trigger.nextElementSibling;
  if (openAssetMenu === menu) {
    closeAssetMenu(true);
    return;
  }
  closeAssetMenu();
  menu.hidden = false;
  menu.classList.toggle("opens-up", trigger.getBoundingClientRect().bottom + 54 > window.innerHeight);
  trigger.setAttribute("aria-expanded", "true");
  openAssetMenu = menu;
  menu.querySelector("[role=menuitem]")?.focus();
}

function closeAssetMenu(restoreFocus = false) {
  if (!openAssetMenu) return;
  const trigger = openAssetMenu.previousElementSibling;
  openAssetMenu.hidden = true;
  trigger?.setAttribute("aria-expanded", "false");
  openAssetMenu = null;
  if (restoreFocus) trigger?.focus();
}

function openAllocationPolicy() {
  if (!currentHoldings) return;
  const dialog = document.querySelector("#allocation-policy-dialog") || document.body.appendChild(document.createElement("dialog"));
  dialog.id = "allocation-policy-dialog";
  dialog.className = "allocation-policy-dialog";
  const rows = currentHoldings.classes.map(group => `<label><span>${group.label}</span><input type="number" name="${group.asset_class}" min="0" max="100" step="0.1" value="${Number(group.target_weight || 0) * 100}"><b>%</b></label>`).join("");
  dialog.innerHTML = `<form method="dialog"><div class="dialog-heading"><div><h2>Configurar alocação ideal</h2><p>Defina o percentual alvo para cada classe. O total deve ser 100%.</p></div><button class="dialog-close" value="cancel" aria-label="Fechar">×</button></div><div class="policy-editor"><div class="policy-preview"><div class="allocation-donut policy-donut"></div><strong>Meta da carteira</strong></div><div class="policy-inputs">${rows}<p id="policy-total">Total 0%</p></div></div><div class="dialog-actions"><button class="secondary" value="cancel">Cancelar</button><button id="save-allocation-policy" value="default">Salvar alterações</button></div></form>`;
  const form = dialog.querySelector("form");
  const updatePreview = () => {
    const inputs = [...form.querySelectorAll("input")];
    const values = inputs.map(input => Math.max(Number(input.value) || 0, 0));
    const total = values.reduce((sum, value) => sum + value, 0);
    form.querySelector("#policy-total").textContent = `Total ${percentage(total)}`;
    const colors = ["#5b8def", "#5b9cff", "#8a6ce8", "#e7b65a", "#e26f95", "#5fc5e6"];
    let start = 0;
    const stops = values.map((value, index) => { const end = start + value; const stop = `${colors[index % colors.length]} ${start}% ${end}%`; start = end; return stop; });
    form.querySelector(".policy-donut").style.background = `conic-gradient(${stops.join(",")})`;
  };
  form.addEventListener("input", updatePreview);
  form.addEventListener("submit", async event => {
    if (event.submitter?.id !== "save-allocation-policy") return;
    event.preventDefault();
    const targets = Object.fromEntries([...form.querySelectorAll("input")].map(input => [input.name, Number(input.value || 0) / 100]));
    if (Math.abs(Object.values(targets).reduce((sum, value) => sum + value, 0) - 1) > 0.000001) {
      form.querySelector("#policy-total").textContent = "O total deve ser exatamente 100%.";
      return;
    }
    await portfolioApi.allocationPolicy(targets);
    dialog.close();
    loadPortfolio();
  });
  updatePreview();
  dialog.showModal();
}

function renderPerformanceSummary(performance) {
  const performanceTarget = document.querySelector("#home-performance");
  const returnTarget = document.querySelector("#home-return");
  if (!performanceTarget && !returnTarget) return;
  const value = period => period?.twr !== null && period?.twr !== undefined
    && ["AVAILABLE", "PARTIAL"].includes(period.status)
    ? `${percentage(Number(period.twr) * 100)}${period.status === "PARTIAL" ? " · parcial" : ""}`
    : "Indisponível";
  const range = period => period?.effective_start_date
    ? `Desde ${new Date(`${period.effective_start_date}T00:00:00`).toLocaleDateString("pt-BR")}`
    : financialConcepts.returnPeriodTotal;
  if (performanceTarget) performanceTarget.innerHTML = performance
    ? `<span title="${escapeHtml(periodTooltip(performance.twelve_months))}"><small>${financialConcepts.returnPeriod12Months}</small>${value(performance.twelve_months)}</span><span title="${escapeHtml(periodTooltip(performance.total))}"><small>${range(performance.total)}</small>${value(performance.total)}</span>`
    : '<span class="unavailable">Indisponível</span>';
  if (returnTarget) {
    const period = performance?.twelve_months;
    returnTarget.textContent = period?.twr !== null && period?.twr !== undefined
      && ["AVAILABLE", "PARTIAL"].includes(period.status)
      ? `${percentage(Number(period.twr) * 100)}${period.status === "PARTIAL" ? " · parcial" : ""}`
      : "Indisponível";
    returnTarget.title = periodTooltip(period);
  }
}

function periodTooltip(period) {
  if (period?.unavailable_reason) return period.unavailable_reason;
  if (period?.status === "PARTIAL" && period.coverage !== null && period.coverage !== undefined) {
    return `${financialConcepts.returnTooltip} Cobertura: ${percentage(Number(period.coverage) * 100)}.`;
  }
  return financialConcepts.returnTooltip;
}

function assetsForDisplay(group) {
  // The read model also includes target-only assets for allocation analysis.
  // They have no position or financial events and must not appear as holdings.
  const positions = group.assets.filter(asset => !asset.target_only);
  if (group.asset_class !== "FIXED_INCOME") return positions;
  const byContract = new Map();
  positions.forEach(asset => {
    // Different fixed-income conditions are different investments, even when
    // the issuer has the same name. The API contract key includes instrument,
    // indexer, contracted rate, CDI percentage and spread.
    const key = asset.contract_key || asset.name.trim().toLocaleUpperCase("pt-BR");
    const lots = byContract.get(key) || [];
    lots.push(asset);
    byContract.set(key, lots);
  });
  return [...byContract.values()].map(lots => {
    const contractLabel = lots[0].contract_label || lots[0].name;
    if (lots.length === 1) return { ...lots[0], lot_count: 1, display_name: contractLabel };
    const sum = key => lots.reduce((total, asset) => total + Number(asset[key] ?? 0), 0);
    const quantity = sum("quantity");
    const cost = lots.reduce((total, asset) => total + Number(asset.average_price ?? 0) * Number(asset.quantity ?? 0), 0);
    const marketValue = lots.some(asset => asset.market_value === null) ? null : sum("market_value");
    const result = lots.some(asset => asset.total_result === null) ? null : sum("total_result");
    return {
      ...lots[0],
      ticker: lots[0].ticker,
      display_name: contractLabel,
      lot_count: lots.length,
      quantity,
      average_price: quantity ? cost / quantity : 0,
      current_price: marketValue === null || !quantity ? null : marketValue / quantity,
      market_value: marketValue,
      total_result: result,
      return_percentage: cost ? ((marketValue ?? cost) - cost) / cost * 100 : 0,
      income_received: sum("income_received"),
      portfolio_weight: lots.some(asset => asset.portfolio_weight === null) ? null : sum("portfolio_weight"),
      target_weight: lots.some(asset => asset.target_weight === null) ? null : sum("target_weight"),
    };
  });
}

function renderHoldingRow(asset, fixedIncome, assetClass, classLabel = assetClass) {
  const title = fixedIncome ? (asset.display_name || asset.name) : asset.ticker;
  const applicationCount = asset.lot_count || 1;
  const subtitle = fixedIncome
    ? `${asset.instrument || "Renda fixa"} · ${asset.indexer || "Condição informada"}${asset.condition ? ` · ${asset.condition}` : ""}`
    : asset.price_as_of ? `Cotação de ${new Date(`${asset.price_as_of}T00:00:00`).toLocaleDateString("pt-BR")}` : "";
  const quantity = fixedIncome
    ? applicationCount
    : asset.quantity;
  const tradeActions = !fixedIncome && !["PENSION", "REAL_ESTATE"].includes(assetClass)
    ? ["BUY", "SELL"].map(type => `<button type="button" role="menuitem" data-open-operation data-operation-type="${type}" data-operation-class="${escapeHtml(assetClass)}" data-operation-ticker="${escapeHtml(asset.ticker)}" data-operation-name="${escapeHtml(asset.name)}" data-operation-country="${escapeHtml(asset.country || "")}" data-operation-currency="${escapeHtml(asset.currency_code || "BRL")}" data-operation-sector="${escapeHtml(asset.sector || "")}">${type === "BUY" ? "Nova compra" : "Registrar venda"}</button>`).join("")
    : "";
  const menu = `<td class="asset-options-cell"><button type="button" class="holding-details-toggle" data-holding-details aria-expanded="false" aria-label="Detalhes de ${escapeHtml(title)}">Mais detalhes</button><button class="asset-options-button" type="button" title="Opções" aria-label="Opções de ${escapeHtml(title)}" aria-haspopup="menu" aria-expanded="false" data-asset-options>⋯</button><div class="asset-context-menu" role="menu" hidden><button type="button" role="menuitem" data-asset-transactions data-asset-id="${escapeHtml(asset.asset_id)}" data-asset-title="${escapeHtml(title)}"><span aria-hidden="true">≡</span> Lançamentos</button>${tradeActions}</div></td>`;
  const fullName = asset.name || title;
  const tickerHint = `title="${escapeHtml(fullName)}" aria-label="${escapeHtml(`${title} — ${fullName}`)}"`;
  return `<tr><td data-label="Ativo"><span class="asset-identity"><i>${escapeHtml(title.slice(0, 2))}</i><span><strong ${tickerHint}>${escapeHtml(title)}</strong><small>${escapeHtml(fullName)}</small><small>${escapeHtml(subtitle)}</small><small class="holding-class-label">${escapeHtml(classLabel)}</small></span></span></td><td data-label="Quantidade">${escapeHtml(quantity)}</td><td data-label="PM">${money(asset.average_price, asset.currency_code)}</td><td data-label="Cotação">${asset.current_price == null ? "Preço não disponível." : money(asset.current_price, asset.currency_code)}</td><td data-label="Saldo">${asset.market_value === null ? "—" : money(asset.market_value, asset.currency_code)}</td><td data-label="Resultado"><b class="metric-pill ${asset.total_result === null ? "" : Number(asset.total_result) < 0 ? "negative" : Number(asset.total_result) > 0 ? "positive" : ""}">${asset.total_result === null ? "Resultado indisponível" : `${Number(asset.total_result) > 0 ? "Ganho +" : Number(asset.total_result) < 0 ? "Perda " : "Sem variação "}${money(asset.total_result, asset.currency_code)}`}</b></td><td data-label="Valorização"><b class="metric-pill ${asset.return_percentage === null ? "" : Number(asset.return_percentage) < 0 ? "negative" : Number(asset.return_percentage) > 0 ? "positive" : ""}">${asset.return_percentage === null ? "—" : `${Number(asset.return_percentage) > 0 ? "+" : ""}${percentage(asset.return_percentage)}`}</b></td><td data-label="Rendimentos">${money(asset.income_received, asset.currency_code)}</td><td data-label="Peso">${asset.portfolio_weight === null ? "—" : percentage(asset.portfolio_weight * 100)}</td><td data-label="Alvo classe">${asset.target_weight === null ? "—" : percentage(asset.target_weight * 100)}</td>${menu.replace('<td class="asset-options-cell"', '<td class="asset-options-cell" data-label="Opções"')}</tr>`;
}

function renderPortfolio(data, holdings, performance) {
  currentHoldings = holdings;
  const capitalGain = Number(data.realized_result || 0) + Number(data.unrealized_result || 0);
  const values = { cash: data.cash, cost: data.total_cost, "market-value": data.total_market_value, "total-result": data.total_result, equity: data.total_market_value, contributions: data.total_contributions, withdrawals: data.total_withdrawals, result: data.realized_result, "unrealized-result": data.unrealized_result, income: data.income_received, "income-in-profit": data.income_received, "capital-gain": capitalGain };
  Object.entries(values).forEach(([id, value]) => {
    const target = document.querySelector(`#${id}`);
    if (target) target.textContent = value === null ? "—" : money(value);
  });
  const netInvested = document.querySelector("#net-invested");
  const capitalAppliedNote = document.querySelector("#capital-applied-note");
  const capitalStatus = data.capital_applied_status;
  if (netInvested) {
    netInvested.textContent = capitalStatus === "AVAILABLE" || capitalStatus === "ZERO"
      ? money(data.capital_applied, data.base_currency || holdings.base_currency)
      : capitalStatus === "PARTIAL"
        ? money(data.capital_applied_partial_amount, data.base_currency || holdings.base_currency)
        : "Indisponível";
  }
  if (capitalAppliedNote) {
    if (capitalStatus === "PARTIAL" || capitalStatus === "UNAVAILABLE") {
      const assets = (data.capital_applied_incomplete_reasons || [])
        .map(item => `${item.ticker} (${item.reason})`).join(", ");
      capitalAppliedNote.textContent = assets
        ? `${capitalStatus === "PARTIAL" ? `Parcial (${data.capital_applied_included_position_count}/${data.capital_applied_position_count} posições). ` : ""}Custo incompleto: ${assets}`
        : "Não foi possível determinar o custo de todas as posições.";
    } else if (capitalStatus === "ZERO") {
      capitalAppliedNote.textContent = "Não há posições abertas com capital aplicado.";
    } else {
      capitalAppliedNote.textContent = "Custo de aquisição das posições atuais";
    }
  }
  if (data.total_market_value === null) {
    const equity = document.querySelector("#equity");
    if (equity) equity.textContent = "Valuation parcial";
  }
  renderPerformanceSummary(performance);
  const returnHeading = document.querySelector("#home-performance-label");
  if (returnHeading) returnHeading.textContent = financialConcepts.returnLabel;
  const returnInfo = document.querySelector(".metric-info");
  if (returnInfo) returnInfo.title = financialConcepts.returnTooltip;
  renderHoldingsCategories();
  const search = document.querySelector("#holdings-search"); if (search) search.value=holdingsQuery;
  const sort = document.querySelector("#holdings-sort"); if (sort) sort.value=holdingsSort;
  renderHoldings();
}
function renderHoldings() {
  const holdings = currentHoldings;
  if (!holdings) return;
  const title = document.querySelector("#positions")?.closest(".card")?.querySelector("h2");
  if (title) title.textContent = "Seus investimentos, em um só lugar";
  if (!document.querySelector("#open-allocation-policy")) title?.insertAdjacentHTML("afterend", '<button class="secondary allocation-policy-trigger" id="open-allocation-policy" type="button"><svg class="income-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><path d="M4 7h6m4 0h6M4 17h10m4 0h2"/><circle cx="12" cy="7" r="2"/><circle cx="16" cy="17" r="2"/></svg><span>Configurar alocação ideal</span></button>');
  document.querySelector("#positions")?.closest(".card")?.classList.add("holdings-card");
  const allGroups = holdings.classes.filter(group => assetsForDisplay(group).length);
  const groups = allGroups.filter(group => !holdingsClass || group.asset_class===holdingsClass).map(group => ({group, assets:selectHoldingAssets(group)})).filter(item => item.assets.length);
  const count = document.querySelector("#holdings-count");
  if (count) count.textContent = `${groups.reduce((sum,item)=>sum+item.assets.length,0)} investimentos encontrados`;
  document.querySelector("#positions").innerHTML = groups.length
    ? groups.map(({group, assets}, index) => {
      const fixedIncome = group.asset_class === "FIXED_INCOME";
      const columns = fixedIncome
        ? ["Contrato", "Aplicações", "PM", "Cotação", "Saldo", "Resultado", "Variação", "Rendimentos", "Peso", "Alvo classe", "Opções"]
        : ["Ativo", "Quantidade", "PM", "Cotação", "Saldo", "Resultado", "Variação", "Rendimentos", "Peso", "Alvo classe", "Opções"];
      const coverage = group.performance_coverage;
      const classTwr = coverage?.twr !== null && coverage?.twr !== undefined
        && ["AVAILABLE", "PARTIAL"].includes(coverage?.status)
        ? `${percentage(Number(coverage.twr) * 100)}${coverage.status === "PARTIAL" ? " · parcial" : ""}`
        : "Indisponível";
      const classPeriod = coverage?.performance_coverage_start_date
        ? `Desde ${new Date(`${coverage.performance_coverage_start_date}T00:00:00`).toLocaleDateString("pt-BR")}`
        : "Período indisponível";
      const classReason = escapeHtml([
        coverage?.unavailable_reason || financialConcepts.returnTooltip,
        coverage?.missing_assets?.length ? `Ativos sem cotação: ${coverage.missing_assets.join(", ")}.` : "",
        coverage?.missing_periods?.length ? `Datas sem cobertura: ${coverage.missing_periods.join(", ")}.` : "",
        coverage?.status === "PARTIAL" && coverage.coverage_ratio !== null && coverage.coverage_ratio !== undefined
          ? `Cobertura no pior ponto: ${percentage(Number(coverage.coverage_ratio) * 100)}.` : "",
      ].filter(Boolean).join(" "));
      const variation = group.total_cost && group.market_value !== null
        ? percentage((Number(group.market_value) - Number(group.total_cost)) / Number(group.total_cost) * 100)
        : "—";
      const chartAvailable = group.market_value !== null && group.assets.some(asset => asset.market_value !== null);
      const groupAction = `<button class="holding-chart-button" type="button" data-group-distribution data-group-id="${escapeHtml(group.asset_class)}" ${chartAvailable ? "" : "disabled"} title="${chartAvailable ? "Gráficos" : "Não há ativos para visualizar."}" aria-label="Gráficos de ${escapeHtml(group.label)}"><svg class="income-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v9h9A9 9 0 1 1 9 3.5M15 3.5a9 9 0 0 1 5.5 5.5H15z"/></svg><span>Distribuição</span></button>`;
      return `<details class="holding-class" data-holdings-group="${escapeHtml(group.asset_class)}" ${(holdingsOpenGroups.get(group.asset_class) ?? (index === 0 || Boolean(holdingsQuery))) ? "open" : ""}><summary><span class="holding-class-name"><strong>${escapeHtml(group.label)}</strong><small>${assets.length} investimento${assets.length === 1 ? "" : "s"}</small></span><span class="holding-class-value"><small>Total da classe</small><strong>${group.market_value === null ? "Valuation parcial" : money(group.market_value, holdings.base_currency)}</strong></span><span class="holding-class-statistics"><span class="holding-class-metric"><small title="Diferença entre o valor atual dos ativos da classe e o custo registrado; não é rentabilidade TWR.">Diferença vs. custo</small><strong>${variation}</strong></span><span class="holding-class-metric"><small title="${classReason}">TWR · desde ${classPeriod.replace("Desde ", "")}</small><strong title="${classReason}">${classTwr}</strong></span><span class="holding-class-metric"><small>Peso atual</small><strong>${group.weight === null ? "—" : percentage(group.weight * 100)}</strong></span>${group.target_weight === null ? "" : `<span class="holding-class-metric"><small>Peso ideal</small><strong>${percentage(group.target_weight * 100)}</strong><small>Desvio ${percentage(group.deviation * 100)}</small></span>`}</span>${groupAction}<span class="holding-class-action" aria-hidden="true"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m7 10 5 5 5-5"/></svg></span></summary>${table(columns, assets.map(asset => renderHoldingRow(asset, fixedIncome, group.asset_class, group.label))).replace("<table>", `<table aria-label="Ativos de ${escapeHtml(group.label)}">`).replaceAll("<th>", '<th scope="col">')}</details>`;
    }).join("")
    : allGroups.length
      ? '<div class="holdings-state"><p>Nenhum investimento encontrado nesta categoria.</p><button type="button" class="income-button secondary" data-holdings-clear>Limpar filtros</button></div>'
      : '<div class="holdings-state"><p>Seus investimentos aparecerão aqui.</p><button type="button" class="income-button" id="holdings-first-operation">Adicionar investimento</button></div>';
}

function openAssetTransactions(assetId, assetTitle, trigger) {
  if (!assetId) return;
  assetTransactionsTrigger = trigger || document.activeElement;
  const dialog = getAssetTransactionsDialog();
  dialog.dataset.assetId = assetId;
  dialog.dataset.assetTitle = assetTitle;
  dialog._eventViews = { movement: { page: 1 }, income: { page: 1 } };
  dialog.querySelector("[data-asset-transactions-title]").textContent = `Lançamentos de ${assetTitle}`;
  dialog.querySelector("[data-asset-transactions-content]").innerHTML = loadingState;
  if (!dialog.open) dialog.showModal();
  loadAssetTransactions(dialog, 1, "SUMMARY");
}

function getAssetTransactionsDialog() {
  let dialog = document.querySelector("#asset-transactions-modal");
  if (dialog) return dialog;
  dialog = document.createElement("dialog");
  dialog.id = "asset-transactions-modal";
  dialog.className = "asset-transactions-dialog";
  dialog.setAttribute("aria-labelledby", "asset-transactions-modal-title");
  dialog.innerHTML = `<div class="dialog-heading"><div><h2 id="asset-transactions-modal-title" data-asset-transactions-title></h2><p data-asset-transactions-subtitle></p></div><button class="dialog-close" type="button" aria-label="Fechar lançamentos" data-close-asset-transactions>×</button></div><div class="asset-transactions-content" data-asset-transactions-content></div>`;
  dialog.addEventListener("click", event => {
    if (event.target.matches("[data-close-asset-transactions]")) dialog.close();
    if (event.target.matches("[data-asset-transactions-page]")) loadAssetTransactions(dialog, Number(event.target.dataset.assetTransactionsPage), event.target.dataset.assetTransactionsGroup);
    if (event.target.matches("[data-retry-asset-transactions]")) loadAssetTransactions(dialog, 1);
    if (event.target.matches("[data-events-tab]")) {
      const key = event.target.dataset.eventsTab;
      const group = key === "income" ? "INCOME" : "MOVEMENT";
      loadAssetTransactions(dialog, dialog._eventViews[key].page, group);
    }
    const groupButton = event.target.closest("[data-open-event-group]");
    if (groupButton) loadAssetTransactions(dialog, 1, groupButton.dataset.openEventGroup);
    const backButton = event.target.closest("[data-events-back]");
    if (backButton) loadAssetTransactions(dialog, 1, "SUMMARY");
    if (event.target.matches("[data-delete-asset-transaction]")) {
      const id = event.target.dataset.deleteAssetTransaction;
      if (!confirm("Excluir este lançamento? A carteira será recalculada.")) return;
      portfolioApi.deleteOperation(id).then(async () => {
        await loadAssetTransactions(dialog, 1);
        await loadPortfolio();
      }).catch(() => { alert("Não foi possível excluir o lançamento."); });
    }
  });
  dialog.addEventListener("close", () => {
    assetTransactionsRequestId += 1;
    assetTransactionsTrigger?.focus();
    assetTransactionsTrigger = null;
  });
  document.body.append(dialog);
  return dialog;
}

async function loadAssetTransactions(dialog, page, group = "MOVEMENT") {
  const requestId = ++assetTransactionsRequestId;
  const content = dialog.querySelector("[data-asset-transactions-content]");
  content.innerHTML = loadingState;
  try {
    const data = await portfolioApi.assetTransactions(dialog.dataset.assetId, { page, page_size: 10, sort: "effective_date_desc", ...(group === "SUMMARY" ? {} : { group }) });
    if (requestId !== assetTransactionsRequestId || !dialog.open) return;
    if (group !== "SUMMARY") dialog._eventViews[group === "INCOME" ? "income" : "movement"].page = page;
    content.innerHTML = renderAssetTransactions(data, group);
  } catch (error) {
    if (requestId !== assetTransactionsRequestId || !dialog.open) return;
    content.innerHTML = `<div class="asset-transactions-error">${errorState("Não foi possível carregar os lançamentos.")}<button type="button" class="secondary" data-retry-asset-transactions>Tentar novamente</button></div>`;
  }
}

function renderAssetTransactions(data, group = "MOVEMENT") {
  if (group === "SUMMARY") return `<div class="asset-events-hub"><section><h3>Movimentações</h3><strong>${data.movement_count}</strong><p>Compras e vendas do ativo.</p><button type="button" data-open-event-group="MOVEMENT">Ver movimentações →</button></section><section><h3>Rendimentos</h3><strong>${data.income_count}</strong><p>Dividendos, JCP e rendimentos.</p><button type="button" data-open-event-group="INCOME">Ver rendimentos →</button></section></div>`;
  if (!data.items.length) return emptyState("Nenhum lançamento encontrado para este ativo.");
  const renderRows = (items, income) => items.map(item => `<tr><td>${escapeHtml(item.operation)}</td><td>${formatDate(item.effective_date)}</td>${income ? "" : `<td>${item.quantity === null ? "—" : item.quantity}</td><td>${item.unit_price === null ? "—" : money(item.unit_price, item.currency_code)}</td>`}<td>${item.amount === null ? "—" : money(item.amount, item.currency_code)}</td><td>${item.source ? escapeHtml(item.source) : "—"}</td><td><button type="button" class="icon-button danger" data-delete-asset-transaction="${item.id}">🗑</button></td></tr>`);
  const movements = group === "MOVEMENT" ? data.items : [];
  const incomes = group === "INCOME" ? data.items : [];
  const pager = data.total_pages > 1 ? `<nav class="asset-transactions-pagination" aria-label="Paginação dos lançamentos"><button class="secondary" type="button" data-asset-transactions-page="${data.page - 1}" ${data.has_previous ? "" : "disabled"}>Anterior</button><span>Página ${data.page} de ${data.total_pages}</span><button class="secondary" type="button" data-asset-transactions-page="${data.page + 1}" ${data.has_next ? "" : "disabled"}>Próximo</button></nav>` : "";
  const movementSection = `<div data-events-pane="movement">${movements.length ? table(["Tipo", "Data", "Quantidade", "Preço unitário", "Valor", "Fonte", "Ações"], renderRows(movements, false)) : emptyState("Nenhuma movimentação registrada para este ativo.")}</div>`;
  const incomeSection = `<div data-events-pane="income" hidden>${incomes.length ? table(["Tipo", "Data", "Valor", "Fonte", "Ações"], renderRows(incomes, true)) : emptyState("Nenhum rendimento registrado para este ativo.")}</div>`;
  const activeMovement = group === "MOVEMENT";
  return `<button class="secondary" type="button" data-events-back>← Lançamentos</button><h3>${activeMovement ? "Movimentações" : "Rendimentos"}</h3>${activeMovement ? movementSection : incomeSection}${pager.replaceAll('data-asset-transactions-page=', `data-asset-transactions-group="${group}" data-asset-transactions-page=`)}`;
}

function formatDate(value) {
  if (!value) return "—";
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);
}

function openGroupDistribution(groupId, trigger) {
  const group = currentHoldings?.classes.find(item => item.asset_class === groupId);
  if (!group || group.market_value === null) return;
  const assets = group.assets
    .filter(asset => asset.market_value !== null)
    .map(asset => ({
      name: asset.contract_label || asset.display_name || asset.ticker || asset.name,
      marketValue: Number(asset.market_value),
      currency: asset.currency_code,
    }))
    .sort((left, right) => right.marketValue - left.marketValue);
  if (!assets.length) return;
  groupDistributionTrigger = trigger;
  const dialog = getGroupDistributionDialog();
  dialog.querySelector("[data-group-distribution-title]").textContent = `${group.label} — Distribuição dos Ativos`;
  dialog.querySelector("[data-group-distribution-content]").innerHTML = renderGroupDistribution(group, assets);
  if (!dialog.open) dialog.showModal();
  renderGroupDistributionChart(dialog, group, assets);
}

function getGroupDistributionDialog() {
  let dialog = document.querySelector("#group-distribution-modal");
  if (dialog) return dialog;
  dialog = document.createElement("dialog");
  dialog.id = "group-distribution-modal";
  dialog.className = "group-distribution-dialog";
  dialog.setAttribute("aria-labelledby", "group-distribution-modal-title");
  dialog.innerHTML = `<div class="dialog-heading"><div><h2 id="group-distribution-modal-title" data-group-distribution-title></h2><p>Participação no valor atual do grupo.</p></div><button class="dialog-close" type="button" aria-label="Fechar distribuição" data-close-group-distribution>×</button></div><div class="group-distribution-content" data-group-distribution-content></div>`;
  dialog.addEventListener("click", event => {
    if (event.target.matches("[data-close-group-distribution]")) dialog.close();
  });
  dialog.addEventListener("close", () => {
    groupDistributionChart?.dispose();
    groupDistributionChart = null;
    groupDistributionTrigger?.focus();
    groupDistributionTrigger = null;
  });
  document.body.append(dialog);
  return dialog;
}

function renderGroupDistribution(group, assets) {
  const total = Number(group.market_value);
  const colors = distributionColors(assets.length);
  const rows = assets.map((asset, index) => {
    const share = asset.marketValue / total * 100;
    return `<button class="group-distribution-row" type="button" data-distribution-index="${index}" title="${escapeHtml(asset.name)}"><i style="background:${colors[index]}"></i><span>${escapeHtml(asset.name)}</span><strong>${money(asset.marketValue, asset.currency)}</strong><b>${percentage(share)}</b></button>`;
  }).join("");
  return `<div class="group-distribution-layout"><div class="group-distribution-donut-wrap"><div id="group-distribution-chart" class="group-distribution-chart" aria-label="Distribuição de ativos de ${escapeHtml(group.label)}"></div><div class="group-distribution-total"><small>Total</small><strong>${money(group.market_value, group.assets[0]?.currency_code || "BRL")}</strong></div></div><div class="group-distribution-legend" aria-label="Legenda da distribuição">${rows}</div></div>`;
}

async function renderGroupDistributionChart(dialog, group, assets) {
  const target = dialog.querySelector("#group-distribution-chart");
  const total = Number(group.market_value);
  const colors = distributionColors(assets.length);
  const echarts = await loadECharts();
  if (!dialog.open || !target?.isConnected) return;
  groupDistributionChart?.dispose();
  groupDistributionChart = echarts.init(target, null, { renderer: "svg" });
  groupDistributionChart.setOption({
    tooltip: { trigger: "item", formatter: item => `${escapeHtml(item.name)}<br>${money(item.value, assets[item.dataIndex].currency)}<br>${percentage(item.percent)}` },
    series: [{ type: "pie", radius: ["58%", "80%"], label: { show: false }, emphasis: { scale: true, scaleSize: 8 }, data: assets.map((asset, index) => ({ name: asset.name, value: asset.marketValue, itemStyle: { color: colors[index] } })) }],
  });
  dialog.querySelectorAll("[data-distribution-index]").forEach(row => {
    row.addEventListener("mouseenter", () => groupDistributionChart?.dispatchAction({ type: "highlight", seriesIndex: 0, dataIndex: Number(row.dataset.distributionIndex) }));
    row.addEventListener("mouseleave", () => groupDistributionChart?.dispatchAction({ type: "downplay", seriesIndex: 0, dataIndex: Number(row.dataset.distributionIndex) }));
    row.addEventListener("focus", () => groupDistributionChart?.dispatchAction({ type: "highlight", seriesIndex: 0, dataIndex: Number(row.dataset.distributionIndex) }));
    row.addEventListener("blur", () => groupDistributionChart?.dispatchAction({ type: "downplay", seriesIndex: 0, dataIndex: Number(row.dataset.distributionIndex) }));
  });
  groupDistributionChart.resize();
}

function distributionColors(count) {
  const palette = ["#5b8def", "#5b9cff", "#8a6ce8", "#e7b65a", "#e26f95", "#5fc5e6", "#d983ff", "#b493e4", "#f28e6b", "#6f95c8"];
  return Array.from({ length: count }, (_, index) => palette[index % palette.length]);
}

function renderHistory(data, baseCurrency = "BRL") {
  const history = document.querySelector("#understand-history");
  if (history) history.innerHTML = data.snapshots.length ? table(["Data", "Patrimônio", "Resultado"], data.snapshots.map(s => `<tr><td>${s.effective_date}</td><td>${s.market_value === null ? "—" : money(s.market_value)}</td><td>${money(s.total_result)}</td></tr>`)) : "Nenhum evento datado registrado.";
  const chart = document.querySelector("#portfolio-evolution");
  if (!chart) return;
  equityChartRequestId += 1;
  disposeEquityChart();
  const points = data.snapshots;
  const selected = value => String(data.period_months) === String(value) ? " selected" : "";
  const selectedClass = value => (data.asset_class || "") === value ? " selected" : "";
  const controls = `<div class="chart-controls"><label>Período <select id="portfolio-history-period"><option value="1"${selected(1)}>1M</option><option value="3"${selected(3)}>3M</option><option value="6"${selected(6)}>6M</option><option value="12"${selected(12)}>12M</option><option value="36"${selected(36)}>3 anos</option><option value="60"${selected(60)}>5 anos</option><option value="120"${selected(120)}>10 anos</option><option value="0"${selected(0)}>Tudo</option></select></label><label>Classe <select id="portfolio-history-class"><option value=""${selectedClass("")}>Todas as classes</option><option value="BRAZILIAN_STOCK"${selectedClass("BRAZILIAN_STOCK")}>Ações Brasil</option><option value="BRAZILIAN_ETF"${selectedClass("BRAZILIAN_ETF")}>ETF Brasil</option><option value="FII"${selectedClass("FII")}>FIIs</option><option value="FIXED_INCOME"${selectedClass("FIXED_INCOME")}>Renda Fixa</option><option value="INTERNATIONAL"${selectedClass("INTERNATIONAL")}>Ações Exterior</option><option value="INTERNATIONAL_ETF"${selectedClass("INTERNATIONAL_ETF")}>ETF Internacional</option><option value="CRYPTO"${selectedClass("CRYPTO")}>Cripto</option><option value="OTHER"${selectedClass("OTHER")}>Outros</option></select></label></div>`;
  if (points.length < 2) {
    chart.innerHTML = `${controls}${emptyState("Evolução indisponível", "Ainda não há dois pontos de histórico para mostrar o saldo patrimonial.")}`;
    return;
  }
  chart.innerHTML = `${controls}<div id="equity-echarts" class="equity-echarts" aria-label="Evolução patrimonial"></div>`;
  renderEquityChart(points, equityChartRequestId, baseCurrency);
}

function disposeEquityChart() {
  equityChartResizeObserver?.disconnect();
  equityChartResizeObserver = null;
  if (equityChart && !equityChart.isDisposed()) equityChart.dispose();
  equityChart = null;
}

function afterLayout() {
  return new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}

async function renderEquityChart(points, requestId, baseCurrency) {
  const target = document.querySelector("#equity-echarts");
  const echarts = await loadECharts();
  // ECharts measures its container at initialization. On the initial dashboard
  // load, the browser can still be calculating the grid width, which produced a
  // narrow chart until the user changed a filter. Wait for two layout frames and
  // keep the chart in sync with later responsive layout changes.
  await afterLayout();
  if (requestId !== equityChartRequestId || !target?.isConnected) return;
  equityChart = echarts.init(target, null, { renderer: "svg" });
  const wealth = points.map(point => point.total_cost === null || point.total_result === null
    ? null : Number(point.total_cost) + Number(point.total_result));
  equityChart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis", formatter: params => `${formatDate(params[0]?.axisValue)}<br><strong>${money(params[0]?.value, baseCurrency)}</strong>` },
    grid: { left: 66, right: 16, top: 20, bottom: 36 },
    xAxis: { type: "category", data: points.map(point => point.effective_date), axisLabel: { color: chartTheme().muted }, axisLine: { lineStyle: { color: chartTheme().border } } },
    yAxis: { type: "value", axisLabel: { color: chartTheme().muted, formatter: value => money(value, baseCurrency) }, splitLine: { lineStyle: { color: chartTheme().border } } },
    series: [{ name: "Patrimônio", type: "line", smooth: true, connectNulls: false, data: wealth, symbol: "circle", symbolSize: 5, lineStyle: { color: chartTheme().accent, width: 3 }, itemStyle: { color: chartTheme().accent }, areaStyle: { color: chartTheme().accent, opacity: .12 } }],
  });
  equityChartResizeObserver = new ResizeObserver(() => equityChart?.resize());
  equityChartResizeObserver.observe(target);
  equityChart.resize();
}

function renderAllocation(data) {
  const target = document.querySelector("#allocation");
  if (!target) return;
  target.innerHTML = data.assets.length ? table(["Ativo", "Peso"], data.assets.map(asset => `<tr><td>${asset.ticker}</td><td>${asset.portfolio_weight === null ? "—" : percentage(asset.portfolio_weight * 100)}</td></tr>`)) : "Nenhuma posição com cotação disponível.";
}

function renderClasses(holdings, fallback) {
  // Allocation is a current-value view in portfolio base currency. Foreign
  // class costs are intentionally unavailable in the holdings read model,
  // while market_value has already been converted to BRL.
  const valued = holdings.classes.filter(item => item.market_value !== null && Number(item.market_value) > 0);
  const total = valued.reduce((sum, item) => sum + Number(item.market_value), 0);
  const colors = { BRAZILIAN_STOCK: "#5b8def", BRAZILIAN_ETF: "#5b9cff", FII: "#8a6ce8", FIXED_INCOME: "#e7b65a", INTERNATIONAL: "#e26f95", INTERNATIONAL_ETF: "#5fc5e6", CRYPTO: "#d983ff", PENSION: "#b493e4", REAL_ESTATE: "#f28e6b", CASH: "#6f95c8", OTHER: "#a3afbf" };
  let cursor = 0;
  const stops = valued.map(item => { const start = cursor; cursor += Number(item.market_value) / total * 100; return `${colors[item.asset_class] || colors.OTHER} ${start}% ${cursor}%`; }).join(", ");
  const content = valued.length ? `<div class="allocation-segmented" role="img" aria-label="Composição por classe: ${holdings.classes.map(item => `${item.label} ${item.market_value === null || !total ? "sem valuation" : percentage(Math.max(Number(item.market_value), 0) / total * 100)}`).join(", ")}"><div class="allocation-segmented-bar">${valued.map(item => `<span title="${escapeHtml(item.label)} · ${money(item.market_value, holdings.base_currency)} · ${percentage(Number(item.market_value) / total * 100)}" style="width:${Math.max(Number(item.market_value) / total * 100, 0.5)}%;background:${colors[item.asset_class] || colors.OTHER}"></span>`).join("")}</div><div class="allocation-legend">${holdings.classes.map(item => { const amount = item.market_value === null ? null : Number(item.market_value); const share = amount === null || !total ? null : Math.max(amount, 0) / total * 100; const detail = amount === null ? "Valuation indisponível" : amount < 0 ? `Saldo negativo · ${money(amount, holdings.base_currency)} · fora da barra` : money(amount, holdings.base_currency); return `<div><i style="background:${colors[item.asset_class] || colors.OTHER}"></i><span>${escapeHtml(item.label)}<small>${detail}</small></span><strong>${share === null ? "—" : percentage(share)}</strong></div>`; }).join("")}</div></div>` : emptyState("Composição indisponível", "Não há saldos positivos avaliados para compor a distribuição.");
  const dashboardTarget = document.querySelector("#class-allocation");
  const legacyStrategyTarget = document.querySelector("#strategy-class-allocation");
  if (dashboardTarget) dashboardTarget.innerHTML = content;
  if (legacyStrategyTarget) {
    legacyStrategyTarget.innerHTML = valued.length
      ? `<div class="allocation-content"><div id="strategy-allocation-chart" class="allocation-chart" aria-label="Distribuição atual por classe"></div><div class="allocation-legend">${holdings.classes.map(item => `<div><i style="background:${colors[item.asset_class] || colors.OTHER}"></i><span>${escapeHtml(item.label)}</span><strong>${item.market_value === null || !total ? "—" : percentage(Number(item.market_value) / total * 100)}</strong></div>`).join("")}</div></div>`
      : emptyState("Composição indisponível", "Não há saldos avaliados para compor a distribuição.");
  }
  const drift = document.querySelector("#portfolio-drift");
  if (drift) drift.textContent = holdings.portfolio_drift === null ? "Estratégia ainda não definida" : `Desvio total ${percentage(holdings.portfolio_drift * 100)}`;
  if (valued.length && legacyStrategyTarget) renderAllocationChart(valued, colors);
}

function renderMonthlyIncome(data) {
  const sequence = ++incomeRenderSequence;
  const target = document.querySelector("#monthly-income-chart");
  if (!target) return;
  incomeChartInstances.forEach(chart => chart.dispose());
  incomeChartInstances = [];
  const { months, byCurrency } = aggregateMonthlyIncome(data.operations || []);
  if (!byCurrency.size) {
    target.innerHTML = emptyState("Sem rendimentos no período", "Dividendos, juros e outros proventos aparecerão aqui quando forem registrados.");
    return;
  }
  target.innerHTML = [...byCurrency.keys()].sort().map((currency, index) => `<div class="monthly-income-unit"><div class="monthly-income-unit-heading"><strong>${escapeHtml(currency)}</strong><small>Valores mantidos na moeda do lançamento</small></div><div class="income-month-chart" data-income-currency="${escapeHtml(currency)}" data-income-index="${index}" aria-label="Rendimentos mensais em ${escapeHtml(currency)}"></div></div>`).join("");
  loadECharts().then(echarts => {
    if (sequence !== incomeRenderSequence) return;
    target.querySelectorAll(".income-month-chart").forEach(chartTarget => {
      if (!chartTarget.isConnected) return;
      const currency = chartTarget.dataset.incomeCurrency;
      const values = byCurrency.get(currency);
      const chart = echarts.init(chartTarget, null, { renderer: "svg" });
      chart.setOption({
        backgroundColor: "transparent",
        tooltip: { trigger: "axis", formatter: params => `${params[0]?.axisValue}<br><strong>${money(params[0]?.value, currency)}</strong>` },
        grid: { left: 62, right: 14, top: 12, bottom: 34 },
        xAxis: { type: "category", data: months.map(month => month.label), axisLabel: { color: chartTheme().muted, hideOverlap: true }, axisLine: { lineStyle: { color: chartTheme().border } } },
        yAxis: { type: "value", axisLabel: { color: chartTheme().muted, formatter: value => money(value, currency) }, splitLine: { lineStyle: { color: chartTheme().border } } },
        series: [{ type: "bar", data: months.map(month => Number(values[month.key] || 0)), barMaxWidth: 32, itemStyle: { color: "#46c98b", borderRadius: [4, 4, 0, 0] } }],
      });
      const observer = new ResizeObserver(() => chart.resize());
      observer.observe(chartTarget);
      incomeChartInstances.push({ resize: () => chart.resize(), isDisposed: () => chart.isDisposed(), setOption: option => chart.setOption(option), dispose: () => { observer.disconnect(); chart.dispose(); } });
    });
  }).catch(error => {
    console.error("Falha ao desenhar rendimentos mensais", error);
    if (sequence === incomeRenderSequence && target.isConnected) target.innerHTML = errorState("Não foi possível desenhar o gráfico de rendimentos.");
  });
}

function aggregateMonthlyIncome(operations, now = new Date()) {
  const incomeTypes = new Set(["DIVIDEND", "INTEREST_ON_EQUITY", "FII_INCOME", "FIXED_INCOME_INTEREST", "STAKING_REWARD"]);
  const months = Array.from({ length: 12 }, (_, index) => {
    const date = new Date(now.getFullYear(), now.getMonth() - 11 + index, 1);
    return { key: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`, label: date.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" }) };
  });
  const monthKeys = new Set(months.map(month => month.key));
  const byCurrency = new Map();
  operations.filter(item => incomeTypes.has(item.type)).forEach(item => {
    const key = String(item.effective_date || "").slice(0, 7);
    if (!monthKeys.has(key)) return;
    const currency = item.currency_code || "BRL";
    const values = byCurrency.get(currency) || Object.fromEntries(months.map(month => [month.key, 0]));
    values[key] += Number(item.amount || 0);
    byCurrency.set(currency, values);
  });
  return { months, byCurrency };
}

async function renderAllocationChart(groups, colors) {
  const target = document.querySelector("#strategy-allocation-chart");
  if (!target) return;
  const echarts = await loadECharts();
  const chart = echarts.init(target, null, { renderer: "svg" });
  chart.setOption({ tooltip: { trigger: "item", formatter: item => `${escapeHtml(item.name)}<br>${money(item.value, currentHoldings?.base_currency || "BRL")}<br>${percentage(item.percent)}` }, series: [{ type: "pie", radius: ["48%", "76%"], label: { show: false }, data: groups.map(group => ({ name: group.label, value: Number(group.market_value), itemStyle: { color: colors[group.asset_class] || colors.OTHER } })) }] });
}
