import { portfolioApi } from "../api.js";
import { emptyState, errorState, money, percentage, table } from "../shared/ui.js";
import { loadECharts } from "../shared/charts.js";

const labels = { BRAZILIAN_STOCK: "Ações Brasil", BRAZILIAN_ETF: "ETF Brasil", FII: "FIIs", FIXED_INCOME: "Renda fixa", INTERNATIONAL: "Ações exterior", INTERNATIONAL_ETF: "ETF internacional", US_REIT: "REITs EUA", CRYPTO: "Cripto", PENSION: "Previdência", REAL_ESTATE: "Imóveis", CASH: "Caixa", OTHER: "Outros" };
let performanceBound = false;
let understandChart = null;
let understandChartResizeObserver = null;
let explanationRequestId = 0;

export function bindPerformance() {
  if (performanceBound) return;
  const form = document.querySelector("#wealth-explanation-form");
  if (!form) return;
  performanceBound = true;
  form.addEventListener("submit", event => { event.preventDefault(); loadExplanation(); });
}

export async function loadExplanation() {
  const requestId = ++explanationRequestId;
  const start = document.querySelector("#wealth-start-date").value;
  const end = document.querySelector("#wealth-end-date").value;
  const target = document.querySelector("#wealth-explanation");
  target.innerHTML = '<div class="empty">Calculando explicação com o histórico persistidoâ€¦</div>';
  try {
    const [data, evolution, comparison] = await Promise.all([portfolioApi.wealthExplanation(start, end), loadWealthEvolution(start, end), portfolioApi.performanceComparison(start, end)]);
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
  target.innerHTML = `<section class="card explanation-headline"><p class="eyebrow">Patrimônio investido</p><h2>${signedMoney(summary.absolute_change)} no saldo de ativos no período</h2><div class="explanation-summary">${summaryRows}</div><p class="coverage">O percentual representa variação do saldo dos ativos e inclui aquisições e vendas; não é rentabilidade da carteira.</p>${valuationNotice}</section><section class="card"><h2>O que fez seu patrimônio mudar?</h2><div class="wealth-bridge"><div class="bridge-row bridge-total"><span>Ativos no início</span><strong>${money(summary.opening_wealth, data.base_currency)}</strong></div>${bridge}<div class="bridge-row bridge-total"><span>Variação dos ativos</span><strong>${signedMoney(summary.absolute_change)}</strong></div></div><p class="coverage">Cobertura da explicação: ${quality.explanation_coverage_percentage === null ? "não aplicável" : percentage(Number(quality.explanation_coverage_percentage))}. Cobertura do valuation: ${percentage(Number(quality.valuation_coverage_percentage || 0))}. ${Number(r.unexplained_change || 0) === 0 ? "A variação foi reconciliada pelos efeitos conhecidos." : `Residual sem causa identificada: ${signedMoney(r.unexplained_change)}.`}</p></section><section class="card"><h2>Rendimentos recebidos no período</h2><div class="explanation-summary"><div><small>Total gerado</small><strong>${money(income.total, data.base_currency)}</strong></div></div><div class="wealth-bridge">${incomeRows}</div><p class="coverage">Rendimentos gerados pelos investimentos. Não são somados ao patrimônio investido quando não permanecem aplicados.</p></section>`;
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

let comparisonChart = null;
let comparisonResizeObserver = null;
async function renderComparison(data, requestId) {
  const target = document.querySelector("#performance");
  const benchmark = Object.fromEntries(data.benchmarks.map(item => [item.code, item]));
  const portfolio = data.portfolio;
  const available = portfolio.return !== null && portfolio.status !== "INSUFFICIENT_DATA";
  const value = amount => amount === null || amount === undefined ? "â€”" : percentage(Number(amount) * 100);
  const points = amount => `${Number(amount) > 0 ? "+" : Number(amount) < 0 ? "âˆ’" : ""}${Math.abs(Number(amount) * 100).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} p.p.`;
  const dateLabel = value => value ? new Date(`${value}T00:00:00`).toLocaleDateString("pt-BR") : "";
  const card = (title, result, extra = "") => `<article class="performance-card"><small>${title}</small><strong>${value(result)}</strong>${extra ? `<span>${extra}</span>` : ""}</article>`;
  const keys = ["CDI", "IBOV", "IFIX"];
  const benchmarkCards = keys.map(code => {
    const item = benchmark[code];
    const excess = available && item?.return !== null && item?.return !== undefined
      ? `Carteira ${points(portfolio.return - Number(item.return))}`
      : item?.status === "STALE" ? `Atualizado até ${dateLabel(item.last_observation)}` : "Referência independente da carteira";
    return card(code, item?.return, excess);
  }).join("");
  const portfolioCard = available
    ? card(portfolio.status === "PARTIAL" ? "Minha carteira · parcial" : "Minha carteira", portfolio.return, portfolio.status === "PARTIAL" ? `Cobertura ${value(portfolio.coverage)}` : "")
    : card("Minha carteira", null, "Rentabilidade indisponível: histórico insuficiente de preços e câmbio.");
  const cards = portfolioCard + benchmarkCards;
  const missingDateText = (portfolio.missing_periods || []).map(dateLabel).join(", ");
  const missingAssets = (portfolio.missing_assets || []).map(item => String(item).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")).join(", ");
  const notice = !available && portfolio.status === "INSUFFICIENT_DATA"
    ? `<aside class="data-quality-notice" role="status"><strong>O que falta para calcular a rentabilidade da carteira</strong><span>${portfolio.unavailable_reason || "Não há valuation de abertura suficiente para calcular o retorno da carteira."}</span>${portfolio.coverage === null ? "" : `<span>Cobertura no pior ponto: ${value(portfolio.coverage)} do patrimônio.</span>`}${portfolio.missing_value && Number(portfolio.missing_value) > 0 ? `<span>As posições sem cotação somam ${money(portfolio.missing_value)} pelo custo registrado; esse valor é uma referência, não uma cotação de mercado.</span>` : ""}${missingDateText ? `<span>Datas sem cobertura suficiente: ${missingDateText}.</span>` : ""}${missingAssets ? `<details><summary>Ver ${portfolio.missing_assets.length} ativos sem cotação</summary><p>${missingAssets}</p></details>` : ""}</aside>`
    : available && portfolio.status === "PARTIAL"
      ? `<p class="coverage" role="status">Performance calculada com cobertura parcial de ${value(portfolio.coverage)} do patrimônio.${portfolio.missing_assets?.length ? ` ${portfolio.missing_assets.length} ativo(s) afetam o cálculo.` : ""}</p>` : "";
  const normalizedSeries = [{ code: "portfolio", label: "Minha carteira", color: "#46c98b", selected: true },
    { code: "cdi", label: "CDI", color: "#78a9ff", selected: true },
    { code: "ibov", label: "IBOV", color: "#e8b86d", selected: false },
    { code: "ifix", label: "IFIX", color: "#c69df2", selected: false },
    { code: "ipca", label: "IPCA", color: "#ef8f9b", selected: false }];
  const hasBenchmarkSeries = data.series.some(point => ["cdi", "ibov", "ifix", "ipca"].some(key => point[key] !== null && point[key] !== undefined));
  const rows = hasBenchmarkSeries ? `<div class="performance-chart-wrap"><div id="performance-comparison-chart" aria-label="Rentabilidade comparada" class="performance-chart"></div></div>` : "";
  const monthly = data.monthly_returns.map(row => `<tr><th>${row.year}-${String(row.month).padStart(2,"0")}</th>${["portfolio","cdi","ibov","ifix","ipca"].map(key => `<td>${value(row[key])}</td>`).join("")}</tr>`).join("");
  const annual = data.annual_returns.map(row => `<tr><th>${row.year}</th>${["portfolio","cdi","ibov","ifix","ipca"].map(key => `<td>${value(row[key])}</td>`).join("")}</tr>`).join("");
  const colNames = ["Período", "Carteira", "CDI", "IBOV", "IFIX", "IPCA"];
  const tableHtml = body => `<div class="performance-table-scroll"><table class="performance-table"><thead><tr>${colNames.map(item => `<th>${item}</th>`).join("")}</tr></thead><tbody>${body || `<tr><td colspan="6">Sem dados para o período.</td></tr>`}</tbody></table></div>`;
  const latestNotes = data.benchmarks.filter(item => item.last_observation && item.status !== "OK").map(item => `${item.code} atualizado até ${dateLabel(item.last_observation)}`).join(" · ");
  const relativeRead = available ? keys.filter(code => benchmark[code]?.return !== null && benchmark[code]?.return !== undefined).map(code => {
    const delta = Number(portfolio.return) - Number(benchmark[code].return);
    return `${points(delta)} ${delta >= 0 ? "acima do" : "abaixo do"} ${code}`;
  }).join("; ") : "";
  target.innerHTML = `<div class="performance-cards">${cards}</div>${notice}<h3>Rentabilidade comparada</h3>${rows ? `<div class="performance-series-toggles">${normalizedSeries.map(item => `<label><input type="checkbox" data-series="${item.code}" ${item.selected ? "checked" : ""}><span style="--series-color:${item.color}"></span>${item.label}</label>`).join("")}</div>${rows}` : ""}<p class="performance-reading">${available ? `No período, sua carteira rendeu ${value(portfolio.return)}. ${relativeRead}.` : "A rentabilidade da carteira não pode ser calculada sem preços de abertura. Os índices disponíveis seguem exibidos acima e nas tabelas."}</p>${latestNotes ? `<p class="coverage">${latestNotes}</p>` : ""}<h3>Rentabilidade mensal</h3>${tableHtml(monthly)}<h3>Comparação anual</h3>${tableHtml(annual)}`;
  if (!rows) return;
  const echarts = await loadECharts();
  const chartTarget = document.querySelector("#performance-comparison-chart");
  if (!chartTarget?.isConnected || requestId !== explanationRequestId) return;
  comparisonResizeObserver?.disconnect();
  comparisonChart?.dispose();
  comparisonChart = echarts.init(chartTarget, null, { renderer: "svg" });
  const selected = () => new Set([...target.querySelectorAll("[data-series]:checked")].map(item => item.dataset.series));
  const applyOption = () => {
    const active = selected();
    comparisonChart.setOption({
      backgroundColor: "transparent", tooltip: { trigger: "axis", valueFormatter: value },
      legend: { show: false }, grid: { left: 58, right: 20, top: 20, bottom: 35 },
      xAxis: { type: "category", data: data.series.map(item => item.date), axisLabel: { color: "#93a4b8" }, axisLine: { lineStyle: { color: "#24364d" } } },
      yAxis: { type: "value", axisLabel: { color: "#93a4b8", formatter: item => `${(Number(item) * 100).toLocaleString("pt-BR", {maximumFractionDigits:1})}%` }, splitLine: { lineStyle: { color: "#203247" } } },
      series: normalizedSeries.filter(item => active.has(item.code)).map(item => ({ name: item.label, type: "line", smooth: true, connectNulls: true, showSymbol: false, data: data.series.map(point => point[item.code]), lineStyle: { color: item.color, width: 2 }, itemStyle: { color: item.color } })),
    }, true);
  };
  applyOption();
  target.querySelectorAll("[data-series]").forEach(input => input.addEventListener("change", applyOption));
  comparisonResizeObserver = new ResizeObserver(() => comparisonChart?.resize());
  comparisonResizeObserver.observe(chartTarget);
}
