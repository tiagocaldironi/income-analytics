import { portfolioApi } from "../api.js?v=20261017-performance-class-filters-v2";
import { emptyState, errorState, money, percentage, table } from "../shared/ui.js";
import { loadECharts } from "../shared/charts.js";

const labels = { BRAZILIAN_STOCK: "Ações Brasil", BRAZILIAN_ETF: "ETF Brasil", FII: "FIIs", FIXED_INCOME: "Renda fixa", INTERNATIONAL: "Ações exterior", INTERNATIONAL_ETF: "ETF internacional", US_REIT: "REITs EUA", CRYPTO: "Cripto", PENSION: "Previdência", REAL_ESTATE: "Imóveis", CASH: "Caixa", OTHER: "Outros" };
let performanceBound = false;
let understandChart = null;
let understandChartResizeObserver = null;
let explanationRequestId = 0;
let selectedComparisonPeriod = "ALL";
let selectedComparisonAssetClass = "";
let contributionChart = null;
let contributionResizeObserver = null;
let contributionData = null;
let contributionLevel = "CLASSES";
let contributionAssetClass = "";

export function bindPerformance() {
  if (performanceBound) return;
  const form = document.querySelector("#wealth-explanation-form");
  if (!form) return;
  performanceBound = true;
  form.addEventListener("submit", event => {
    event.preventDefault();
    selectedComparisonPeriod = "CUSTOM";
    loadExplanation();
  });
}

export async function loadExplanation() {
  const requestId = ++explanationRequestId;
  const start = document.querySelector("#wealth-start-date").value;
  const end = document.querySelector("#wealth-end-date").value;
  const target = document.querySelector("#wealth-explanation");
  target.innerHTML = '<div class="empty">Calculando explicação com o histórico persistido…</div>';
  try {
    let comparisonStart = start;
    if (selectedComparisonPeriod === "ALL") {
      const range = await portfolioApi.performanceComparison(start, end, selectedComparisonAssetClass);
      if (requestId !== explanationRequestId) return;
      const starts = range.available_start_dates || {};
      comparisonStart = starts[selectedComparisonAssetClass || "ALL"] || start;
    } else if (selectedComparisonPeriod === "12M") {
      comparisonStart = dateMinusMonths(end, 12);
    }
    const [data, evolution, comparison] = await Promise.all([
      portfolioApi.wealthExplanation(start, end),
      loadWealthEvolution(start, end),
      portfolioApi.performanceComparison(comparisonStart, end, selectedComparisonAssetClass),
    ]);
    if (requestId !== explanationRequestId) return;
    document.querySelector("#wealth-end-date").value = data.period.end_date;
    const domStarted = performance.now();
    renderExplanation(data, comparison);
    await renderComparison(comparison, requestId);
    performance.measure("income:entender-dom-render", { start: domStarted, end: performance.now() });
    await renderWealthEvolution(evolution, requestId);
  } catch (error) {
    if (requestId === explanationRequestId) target.innerHTML = errorState(error.message);
  }
}

function dateMinusMonths(isoDate, months) {
  if (!isoDate) return "";
  const result = new Date(`${isoDate}T00:00:00`);
  const originalDay = result.getDate();
  result.setMonth(result.getMonth() - months);
  if (result.getDate() !== originalDay) result.setDate(0);
  return `${result.getFullYear()}-${String(result.getMonth() + 1).padStart(2, "0")}-${String(result.getDate()).padStart(2, "0")}`;
}

async function loadWealthEvolution(start, end) {
  try {
    return await portfolioApi.wealthEvolution(start, end);
  } catch {
    const history = await portfolioApi.historyRange(start, end);
    return {
      history_boundary: history.history_boundary,
      points: history.snapshots.map(point => ({
        effective_date: point.effective_date,
        valued_wealth: point.market_value,
        coverage_status: point.market_value === null ? "PARTIAL" : "COMPLETE",
        unvalued_positions: [],
      })),
    };
  }
}

function renderExplanation(data, comparison) {
  const target = document.querySelector("#wealth-explanation");
  const { summary, reconciliation: r, data_quality: quality, income_generated: income } = data;
  const signedMoney = value => `${Number(value) > 0 ? "+" : Number(value) < 0 ? "−" : ""}${money(Math.abs(Number(value)), data.base_currency)}`;
  const valuationNotice = quality.valuation_complete ? "" : `<aside class="data-quality-notice" role="status"><strong>Valuation histórico incompleto</strong><span>Algumas posições não têm preço ou câmbio histórico suficiente. Elas continuam registradas; isso não representa ausência desses ativos. Cobertura do valuation: ${percentage(Number(quality.valuation_coverage_percentage || 0))}.</span></aside>`;
  const changePercent = summary.percentage_wealth_change === null ? "—" : percentage(Number(summary.percentage_wealth_change) * 100);
  const summaryRows = `<div><small>Ativos no início</small><strong>${money(summary.opening_wealth, data.base_currency)}</strong></div><div><small>Ativos no fim</small><strong>${money(summary.closing_wealth, data.base_currency)}</strong></div><div><small>Variação do saldo dos ativos</small><strong>${signedMoney(summary.absolute_change)} · ${changePercent}</strong></div>`;
  const bridge = data.components.map(item => contributionExplorer(item, signedMoney)).join("");
  const incomeRows = [["Dividendos", income.dividends], ["JCP", income.jcp], ["FIIs", income.fii_income], ["Outros rendimentos", income.other_distributed_income]]
    .filter(([, amount]) => Number(amount) !== 0)
    .map(([label, amount]) => `<div class="bridge-row"><span>${label}</span><strong>${signedMoney(amount)}</strong></div>`).join("");
  target.innerHTML = `<section class="card explanation-headline"><p class="eyebrow">Patrimônio investido</p><h2>${signedMoney(summary.absolute_change)} no saldo de ativos no período</h2><div class="explanation-summary">${summaryRows}</div><p class="coverage">O percentual representa variação do saldo dos ativos e inclui aquisições e vendas; não é rentabilidade da carteira.</p>${valuationNotice}</section><section class="card contribution-chart-card"><div class="section-heading"><div><h2>Contribuição para o resultado</h2><p>Explore o resultado por classe, ativo ou fator.</p></div><div class="contribution-controls"><label>Nível<select id="contribution-level"><option value="CLASSES">Classes</option><option value="ASSETS">Ativos</option><option value="FACTORS">Fatores</option></select></label><label id="contribution-class-wrap" hidden>Classe<select id="contribution-class"></select></label></div></div><div id="wealth-contribution-chart" class="wealth-contribution-chart" aria-label="Contribuição divergente por classe de ativo"></div><p id="contribution-chart-note" class="coverage"></p></section><section class="card"><h2>O que fez seu patrimônio mudar?</h2><div class="wealth-bridge"><div class="bridge-row bridge-total"><span>Ativos no início</span><strong>${money(summary.opening_wealth, data.base_currency)}</strong></div>${bridge}<div class="bridge-row bridge-total"><span>Variação dos ativos</span><strong>${signedMoney(summary.absolute_change)}</strong></div></div><p class="coverage">Cobertura da explicação: ${quality.explanation_coverage_percentage === null ? "não aplicável" : percentage(Number(quality.explanation_coverage_percentage))}. Cobertura do valuation: ${percentage(Number(quality.valuation_coverage_percentage || 0))}. ${Number(r.unexplained_change || 0) === 0 ? "A variação foi reconciliada pelos efeitos conhecidos." : `Residual sem causa identificada: ${signedMoney(r.unexplained_change)}.`}</p></section><section class="card"><h2>Rendimentos recebidos no período</h2><div class="explanation-summary"><div><small>Total gerado</small><strong>${money(income.total, data.base_currency)}</strong></div></div><div class="wealth-bridge">${incomeRows}</div><p class="coverage">Rendimentos gerados pelos investimentos. Não são somados ao patrimônio investido quando não permanecem aplicados.</p></section>`;
  contributionData = data;
  renderContributionExplorer(data);
}

function renderContributionExplorer(data) {
  const target = document.querySelector("#wealth-contribution-chart");
  if (!target) return;
  contributionResizeObserver?.disconnect();
  contributionResizeObserver = null;
  contributionChart?.dispose();
  contributionChart = null;
  const levelSelect = document.querySelector("#contribution-level");
  const classWrap = document.querySelector("#contribution-class-wrap");
  const classSelect = document.querySelector("#contribution-class");
  if (!levelSelect || !classWrap || !classSelect) return;
  levelSelect.value = contributionLevel;
  const rows = buildContributionRows(data);
  const classNames = [...new Set(rows.map(row => row.asset_class))];
  if (!contributionAssetClass || !classNames.includes(contributionAssetClass)) contributionAssetClass = classNames[0] || "";
  classWrap.hidden = contributionLevel !== "ASSETS";
  classSelect.innerHTML = classNames.map(assetClass => `<option value="${assetClass}">${labels[assetClass] || assetClass}</option>`).join("");
  classSelect.value = contributionAssetClass;
  if (levelSelect.dataset.bound !== "true") {
    levelSelect.dataset.bound = "true";
    levelSelect.addEventListener("change", () => { contributionLevel = levelSelect.value; renderContributionExplorer(contributionData); });
    classSelect.addEventListener("change", () => { contributionAssetClass = classSelect.value; renderContributionExplorer(contributionData); });
  }
  const note = document.querySelector("#contribution-chart-note");
  const quality = data.data_quality || {};
  note.textContent = `Aportes e retiradas ficam fora da contribuição. Rendimentos recebidos entram como fator separado. ${quality.valuation_complete ? "Valuation completo no período." : `Valuation parcial (${percentage(Number(quality.valuation_coverage_percentage || 0))}); posições pendentes aparecem identificadas.`} O detalhamento de efeito cambial e custos não está disponível neste relatório.`;

  let categories = [];
  let values = [];
  let chartTitle = "Contribuição por classe";
  let detailByCategory = new Map();
  if (contributionLevel === "FACTORS") {
    const factorLabels = { MARKET_VALUATION: "Valorização de mercado", FIXED_INCOME_ACCRUAL: "Renda fixa", VALUATION_ADJUSTMENTS: "Ajustes de valuation", PAID_INCOME: "Rendimentos recebidos", UNEXPLAINED: "Variação não explicada" };
    const factors = new Map();
    for (const component of data.components || []) {
      if (component.component_type === "NET_ACQUISITIONS") continue;
      factors.set(component.component_type, Number(component.signed_amount || 0));
    }
    factors.set("PAID_INCOME", Number(data.income_generated?.total || 0));
    categories = [...factors.keys()].map(key => factorLabels[key] || key);
    values = [...factors.values()];
    chartTitle = "Contribuição por fator";
    detailByCategory = new Map(categories.map((name, index) => [name, [`${money(values[index], data.base_currency)}`]]));
  } else {
    let visible = rows;
    if (contributionLevel === "ASSETS") {
      visible = rows.filter(row => row.asset_class === contributionAssetClass);
      chartTitle = `Contribuição por ativo · ${labels[contributionAssetClass] || contributionAssetClass}`;
    }
    const grouped = new Map();
    for (const row of visible) {
      const name = contributionLevel === "CLASSES" ? (labels[row.asset_class] || row.asset_class) : row.name;
      const current = grouped.get(name) || { value: 0, details: [], asset_class: row.asset_class };
      current.value += row.value;
      current.details.push(`${row.name}: ${money(row.value, data.base_currency)}${row.valuation_available ? "" : " (valuation pendente)"}`);
      grouped.set(name, current);
    }
    const ordered = [...grouped.entries()].sort((a, b) => Math.abs(b[1].value) - Math.abs(a[1].value));
    categories = ordered.map(([name]) => name);
    values = ordered.map(([, item]) => item.value);
    detailByCategory = new Map(ordered.map(([name, item]) => [name, item.details]));
  }
  target.setAttribute("aria-label", chartTitle);
  if (!categories.length) {
    target.innerHTML = emptyState("Sem contribuição detalhada", "Não há componentes financeiros para este período.");
    return;
  }
  const height = Math.max(230, categories.length * 38 + 62);
  target.innerHTML = `<div class="diverging-chart" style="height:${height}px"></div>`;
  loadECharts().then(echarts => {
    const chartTarget = target.querySelector(".diverging-chart");
    if (!chartTarget?.isConnected) return;
    contributionChart = echarts.init(chartTarget, null, { renderer: "svg" });
    contributionChart.setOption({
      backgroundColor: "transparent",
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, formatter: params => { const item = params[0]; const details = detailByCategory.get(item.name) || []; return `<strong>${escapeChartText(item.name)}</strong><br>${item.value > 0 ? "+" : item.value < 0 ? "−" : ""}${money(Math.abs(Number(item.value)), data.base_currency)}${details.length ? `<br><small>${details.map(escapeChartText).join("<br>")}</small>` : ""}`; } },
      grid: { left: 130, right: 18, top: 10, bottom: 26 },
      xAxis: { type: "value", axisLabel: { color: "#93a4b8", formatter: value => money(value, data.base_currency) }, axisLine: { lineStyle: { color: "#41546a" } }, splitLine: { lineStyle: { color: "#203247" } } },
      yAxis: { type: "category", inverse: true, data: categories, axisLabel: { color: "#c6d2df", width: 120, overflow: "truncate" }, axisLine: { show: false }, axisTick: { show: false } },
      series: [{ type: "bar", barMaxWidth: 24, data: values.map(value => ({ value, itemStyle: { color: value < 0 ? "#f06c75" : "#46c98b", borderRadius: value < 0 ? [0, 4, 4, 0] : [0, 4, 4, 0] } })) }],
    });
    contributionResizeObserver = new ResizeObserver(() => contributionChart?.resize());
    contributionResizeObserver.observe(chartTarget);
    if (contributionLevel === "CLASSES") contributionChart.on("click", params => {
      const match = classNames.find(assetClass => (labels[assetClass] || assetClass) === params.name);
      if (match) { contributionAssetClass = match; contributionLevel = "ASSETS"; renderContributionExplorer(contributionData); }
    });
  }).catch(error => {
    console.error("Falha ao desenhar contribuições", error);
    if (target.isConnected) target.innerHTML = errorState("Não foi possível desenhar as contribuições.");
  });
}

function buildContributionRows(data) {
  const assetRows = new Map();
  for (const component of data.components || []) {
    if (["NET_ACQUISITIONS", "UNEXPLAINED"].includes(component.component_type)) continue;
    for (const child of component.children || []) {
      const key = child.ticker || child.label || "Sem identificação";
      const row = assetRows.get(key) || { name: key, ticker: child.ticker || key, asset_class: child.asset_class || "OTHER", factors: {}, valuation_available: true };
      row.factors[component.component_type] = (row.factors[component.component_type] || 0) + Number(child.signed_amount || 0);
      row.valuation_available &&= child.valuation_available !== false;
      assetRows.set(key, row);
    }
  }
  for (const income of data.income_generated?.items || []) {
    const key = income.ticker || income.label || "Sem identificação";
    const row = assetRows.get(key) || { name: key, ticker: income.ticker || key, asset_class: income.asset_class || "OTHER", factors: {}, valuation_available: true };
    row.factors.PAID_INCOME = (row.factors.PAID_INCOME || 0) + Number(income.signed_amount || 0);
    assetRows.set(key, row);
  }
  return [...assetRows.values()].map(row => ({ ...row, value: Object.values(row.factors).reduce((sum, value) => sum + value, 0) }));
}

async function renderWealthEvolution(evolution, requestId) {
  const chartStarted = performance.now();
  understandChartResizeObserver?.disconnect();
  understandChartResizeObserver = null;
  understandChart?.dispose();
  understandChart = null;
  const target = document.querySelector("#understand-history");
  const points = evolution.points;
  const valuedPoints = points.filter(item => item.valued_wealth !== null);
  if (valuedPoints.length < 2) {
    target.innerHTML = emptyState("Evolução indisponível", "Ainda não há ao menos dois pontos historicamente avaliáveis no período selecionado.");
    return;
  }
  target.innerHTML = '<div id="understand-evolution-chart" class="equity-echarts" aria-label="Evolução do saldo dos ativos no período"></div>';
  const chartTarget = document.querySelector("#understand-evolution-chart");
  const echarts = await loadECharts();
  if (requestId !== explanationRequestId || !chartTarget?.isConnected) return;
  understandChart = echarts.init(chartTarget, null, { renderer: "svg" });
  understandChart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis", valueFormatter: value => money(value) },
    grid: { left: 64, right: 18, top: 20, bottom: 38 },
    xAxis: { type: "category", data: points.map(item => item.effective_date), axisLabel: { color: "#93a4b8" }, axisLine: { lineStyle: { color: "#24364d" } } },
    yAxis: { type: "value", axisLabel: { color: "#93a4b8", formatter: value => `R$ ${Number(value).toLocaleString("pt-BR")}` }, splitLine: { lineStyle: { color: "#203247" } } },
    series: [{ name: "Parcela avaliável dos ativos", type: "line", smooth: true, connectNulls: false, data: points.map(item => item.valued_wealth === null ? null : Number(item.valued_wealth)), symbol: "circle", symbolSize: 5, lineStyle: { color: "#46c98b", width: 3 }, itemStyle: { color: "#46c98b" }, areaStyle: { color: "rgba(70, 201, 139, .14)" } }],
  });
  understandChartResizeObserver = new ResizeObserver(() => understandChart?.resize());
  understandChartResizeObserver.observe(chartTarget);
  const partial = points.some(item => item.coverage_status === "PARTIAL");
  if (partial) {
    const missing = [...new Set(points.flatMap(item => item.unvalued_positions.map(position => labels[position.asset_class] || position.asset_class)))];
    target.insertAdjacentHTML("beforeend", `<p class="coverage">Evolução do saldo dos ativos com valuation disponível. Classes sem valuation em parte do período: ${missing.join(", ") || "não identificadas"}.</p>`);
  }
  performance.measure("income:entender-chart-render", { start: chartStarted, end: performance.now() });
}

function contributionExplorer(item, signedMoney) {
  const children = item.children.filter(child => Number(child.signed_amount) !== 0);
  if (!children.length) return `<details class="bridge-row"><summary><span>${item.label}</span><strong>${signedMoney(item.signed_amount)}</strong></summary></details>`;
  const top = [...children].sort((a, b) => Math.abs(Number(b.signed_amount)) - Math.abs(Number(a.signed_amount))).slice(0, 3);
  const groups = children.reduce((all, child) => {
    const key = child.asset_class || "OTHER";
    (all[key] ||= []).push(child);
    return all;
  }, {});
  const topRows = top.map(child => `<div class="contribution-impact"><span>${child.ticker || child.label}${child.valuation_available === false ? " · valuation pendente" : ""}</span><strong>${signedMoney(child.signed_amount)}</strong></div>`).join("");
  const classRows = Object.entries(groups).sort(([, left], [, right]) => sumSigned(right) - sumSigned(left)).map(([assetClass, entries]) => `<details class="contribution-class"><summary><span>${labels[assetClass] || assetClass}</span><strong>${signedMoney(sumSigned(entries))}</strong></summary><div class="contribution-assets">${entries.sort((a, b) => Math.abs(Number(b.signed_amount)) - Math.abs(Number(a.signed_amount))).map(child => `<div><span>${child.ticker || child.label}${child.valuation_available === false ? " · valuation pendente" : ""}</span><strong>${signedMoney(child.signed_amount)}</strong></div>`).join("")}</div></details>`).join("");
  return `<details class="bridge-row contribution-explorer"><summary><span>${item.label}</span><strong>${signedMoney(item.signed_amount)}</strong></summary><div class="contribution-summary"><small>${children.length} ativo${children.length === 1 ? "" : "s"} contribuíram para esta variação</small><h3>Maiores impactos</h3>${topRows}<h3>Por classe</h3>${classRows}</div></details>`;
}

function sumSigned(items) { return items.reduce((sum, item) => sum + Number(item.signed_amount), 0); }

function escapeChartText(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
}

let comparisonChart = null;
let comparisonResizeObserver = null;
async function renderComparison(data, requestId) {
  const target = document.querySelector("#performance");
  const benchmark = Object.fromEntries(data.benchmarks.map(item => [item.code, item]));
  const portfolio = data.portfolio;
  const portfolioLabel = data.asset_class ? labels[data.asset_class] || data.asset_class : "Minha carteira";
  const available = portfolio.return !== null && portfolio.status !== "INSUFFICIENT_DATA";
  const value = amount => amount === null || amount === undefined ? "—" : percentage(Number(amount) * 100);
  const points = amount => `${Number(amount) > 0 ? "+" : Number(amount) < 0 ? "−" : ""}${Math.abs(Number(amount) * 100).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} p.p.`;
  const dateLabel = value => value ? new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR") : "";
  const card = (title, result, extra = "") => `<article class="performance-card"><small>${title}</small><strong>${value(result)}</strong>${extra ? `<span>${extra}</span>` : ""}</article>`;
  const keys = ["CDI", "IPCA", "IBOV", "IFIX", "SMLL", "IDIV", "IVVB11"];
  const benchmarkCards = keys.map(code => {
    const item = benchmark[code];
    const excess = available && item?.return !== null && item?.return !== undefined
      ? `${portfolioLabel} ${points(portfolio.return - Number(item.return))}`
      : item?.status === "STALE" ? `Atualizado até ${dateLabel(item.last_observation)}` : "Referência independente da carteira";
    return card(code, item?.return, excess);
  }).join("");
  const portfolioCard = available
    ? card(portfolio.status === "PARTIAL" ? `${portfolioLabel} · parcial` : portfolioLabel, portfolio.return, portfolio.status === "PARTIAL" ? `Cobertura ${value(portfolio.coverage)}` : "")
    : card(portfolioLabel, null, "Rentabilidade indisponível para o período selecionado.");
  const cards = portfolioCard + benchmarkCards;
  const missingDateText = (portfolio.missing_periods || []).map(dateLabel).join(", ");
  const missingAssets = (portfolio.missing_assets || []).map(item => String(item).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")).join(", ");
  const notice = !available && portfolio.status === "INSUFFICIENT_DATA"
    ? `<aside class="data-quality-notice" role="status"><strong>O que falta para calcular a rentabilidade de ${portfolioLabel}</strong><span>${portfolio.unavailable_reason || "Não há valuation de abertura suficiente para calcular o retorno selecionado."}</span>${portfolio.coverage === null ? "" : `<span>Cobertura no pior ponto: ${value(portfolio.coverage)} do patrimônio.</span>`}${portfolio.missing_value && Number(portfolio.missing_value) > 0 ? `<span>As posições sem cotação somam ${money(portfolio.missing_value)} pelo custo registrado; esse valor é uma referência, não uma cotação de mercado.</span>` : ""}${missingDateText ? `<span>Datas sem cobertura suficiente: ${missingDateText}.</span>` : ""}${missingAssets ? `<details><summary>Ver ${portfolio.missing_assets.length} posições sem valuation</summary><p>${missingAssets}</p></details>` : ""}</aside>`
    : available && portfolio.status === "PARTIAL"
      ? `<p class="coverage" role="status">Performance calculada com cobertura parcial de ${value(portfolio.coverage)} do patrimônio.${portfolio.missing_assets?.length ? ` ${portfolio.missing_assets.length} ativo(s) afetam o cálculo.` : ""}</p>` : "";
  const normalizedSeries = [
    { code: "portfolio", label: portfolioLabel, color: "#829cf3" },
    { code: "cdi", label: "CDI", color: "#ffbd45" },
    { code: "ipca", label: "IPCA", color: "#7cc65e" },
    { code: "ifix", label: "IFIX", color: "#9e4a18" },
    { code: "ibov", label: "IBOV", color: "#b7b7b7" },
    { code: "smll", label: "SMLL", color: "#c9c9c9" },
    { code: "idiv", label: "IDIV", color: "#ff784d" },
    { code: "ivvb11", label: "IVVB11", color: "#9b59b6" },
  ];
  const benchmarkSeriesKeys = keys.map(code => code.toLowerCase());
  const hasBenchmarkSeries = data.series.some(point => benchmarkSeriesKeys.some(key => point[key] !== null && point[key] !== undefined));
  const rows = hasBenchmarkSeries ? `<div class="performance-chart-wrap"><div id="performance-comparison-chart" aria-label="Rentabilidade comparada" class="performance-chart"></div></div>` : "";
  const availableClasses = data.available_asset_classes || [];
  const classOptions = availableClasses.map(assetClass => `<option value="${assetClass}" ${assetClass === selectedComparisonAssetClass ? "selected" : ""}>${labels[assetClass] || assetClass}</option>`).join("");
  const comparisonFilters = `<div class="performance-filter-controls"><label>Período<select id="performance-period-filter"><option value="ALL" ${selectedComparisonPeriod === "ALL" ? "selected" : ""}>Desde o início</option><option value="12M" ${selectedComparisonPeriod === "12M" ? "selected" : ""}>Últimos 12 meses</option><option value="CUSTOM" ${selectedComparisonPeriod === "CUSTOM" ? "selected" : ""}>Período selecionado</option></select></label><label>Categoria<select id="performance-class-filter"><option value="" ${selectedComparisonAssetClass ? "" : "selected"}>Todos os tipos</option>${classOptions}</select></label></div>`;
  const comparisonKeys = ["portfolio", ...benchmarkSeriesKeys];
  const monthly = data.monthly_returns.map(row => `<tr><th>${row.year}-${String(row.month).padStart(2,"0")}</th>${comparisonKeys.map((key, index) => `<td data-label="${index === 0 ? portfolioLabel : keys[index - 1]}">${value(row[key])}</td>`).join("")}</tr>`).join("");
  const annual = data.annual_returns.map(row => `<tr><th>${row.year}</th>${comparisonKeys.map((key, index) => `<td data-label="${index === 0 ? portfolioLabel : keys[index - 1]}">${value(row[key])}</td>`).join("")}</tr>`).join("");
  const colNames = ["Período", "Carteira", ...keys];
  const tableHtml = body => `<div class="performance-table-scroll"><table class="performance-table"><thead><tr>${colNames.map(item => `<th>${item}</th>`).join("")}</tr></thead><tbody>${body || `<tr><td colspan="${colNames.length}">Sem dados para o período.</td></tr>`}</tbody></table></div>`;
  const latestNotes = data.benchmarks.filter(item => item.last_observation && item.status !== "OK").map(item => `${item.code} atualizado até ${dateLabel(item.last_observation)}`).join(" · ");
  const relativeRead = available ? keys.filter(code => benchmark[code]?.return !== null && benchmark[code]?.return !== undefined).map(code => {
    const delta = Number(portfolio.return) - Number(benchmark[code].return);
    return `${points(delta)} ${delta >= 0 ? "acima do" : "abaixo do"} ${code}`;
  }).join("; ") : "";
  target.innerHTML = `<div class="performance-cards">${cards}</div>${notice}<div class="performance-comparison-heading"><h3>Rentabilidade comparada com índices</h3>${comparisonFilters}</div>${rows ? rows : ""}<p class="performance-reading">${available ? `No período, ${portfolioLabel.toLowerCase()} rendeu ${value(portfolio.return)}. ${relativeRead}.` : "A rentabilidade selecionada não pode ser calculada sem dados suficientes. As referências de mercado continuam exibidas."}</p>${latestNotes ? `<p class="coverage">${latestNotes}</p>` : ""}<h3>Rentabilidade mensal</h3>${tableHtml(monthly)}<h3>Comparação anual</h3>${tableHtml(annual)}`;
  target.querySelector("#performance-period-filter")?.addEventListener("change", event => {
    selectedComparisonPeriod = event.target.value;
    loadExplanation();
  });
  target.querySelector("#performance-class-filter")?.addEventListener("change", event => {
    selectedComparisonAssetClass = event.target.value;
    loadExplanation();
  });
  if (!rows) return;
  const echarts = await loadECharts();
  const chartTarget = document.querySelector("#performance-comparison-chart");
  if (!chartTarget?.isConnected || requestId !== explanationRequestId) return;
  comparisonResizeObserver?.disconnect();
  comparisonChart?.dispose();
  comparisonChart = echarts.init(chartTarget, null, { renderer: "svg" });
  const applyOption = () => {
    comparisonChart.setOption({
      backgroundColor: "transparent", tooltip: { trigger: "axis", valueFormatter: value },
      legend: { type: "scroll", top: 0, textStyle: { color: "#93a4b8" }, selectedMode: true }, grid: { left: 58, right: 20, top: 42, bottom: 35 },
      xAxis: { type: "category", data: data.series.map(item => item.date), axisLabel: { color: "#93a4b8" }, axisLine: { lineStyle: { color: "#24364d" } } },
      yAxis: { type: "value", axisLabel: { color: "#93a4b8", formatter: item => `${(Number(item) * 100).toLocaleString("pt-BR", {maximumFractionDigits:1})}%` }, splitLine: { lineStyle: { color: "#203247" } } },
      series: normalizedSeries.map(item => ({ name: item.label, type: "line", smooth: true, connectNulls: true, showSymbol: false, data: data.series.map(point => point[item.code]), lineStyle: { color: item.color, width: 2 }, itemStyle: { color: item.color } })),
    }, true);
  };
  applyOption();
  comparisonResizeObserver = new ResizeObserver(() => comparisonChart?.resize());
  comparisonResizeObserver.observe(chartTarget);
}
