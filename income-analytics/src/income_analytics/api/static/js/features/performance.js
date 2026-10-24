import { portfolioApi } from "../api.js?v=20261017-performance-class-filters-v2";
import { errorState, money, percentage } from "../shared/ui.js";

const labels = { BRAZILIAN_STOCK: "Ações Brasil", BRAZILIAN_ETF: "ETF Brasil", FII: "FIIs", FIXED_INCOME: "Renda fixa", INTERNATIONAL: "Ações exterior", INTERNATIONAL_ETF: "ETF internacional", US_REIT: "REITs EUA", CRYPTO: "Cripto", PENSION: "Previdência", REAL_ESTATE: "Imóveis", CASH: "Caixa", OTHER: "Outros" };
let performanceBound = false;
let explanationRequestId = 0;
let contributionData = null;
const understandAnalyses = [
  { id: "asset-contributions", question: "Quais investimentos mais ganharam ou perderam valor?", service: "wealth-explanation", filters: ["asset_class", "direction", "metric"], render: renderAssetContributionAnswer },
  { id: "wealth-bridge", question: "O que fez meu patrimônio aumentar ou diminuir?", service: "wealth-explanation", filters: [], render: renderWealthBridgeAnswer },
  { id: "paid-income", question: "Quais investimentos geraram mais renda?", service: "wealth-explanation", filters: ["asset_class"], render: renderIncomeAnswer },
  { id: "fixed-income", question: "Quanto minha renda fixa valorizou?", service: "wealth-explanation", filters: ["asset_class"], render: renderFixedIncomeAnswer },
];
let selectedUnderstandAnalysis = "asset-contributions";
let contributionDirection = "ALL";
let rankingShowAll = false;
let expandedAsset = "";
let rankingClassFilter = "";
let incomeClassFilter = "";

export function bindPerformance() {
  if (performanceBound) return;
  const form = document.querySelector("#wealth-explanation-form");
  if (!form) return;
  performanceBound = true;
  const period = document.querySelector("#understand-period-disclosure");
  const startInput = document.querySelector("#wealth-start-date");
  const endInput = document.querySelector("#wealth-end-date");
  const validation = document.querySelector("#understand-period-validation");
  const status = document.querySelector("#understand-period-status");
  const cancel = document.querySelector(".period-cancel");
  const updateLabel = () => {
    const label = document.querySelector("#wealth-period-label");
    if (label && startInput.value && endInput.value) label.textContent = `${formatPeriodDate(startInput.value)} — ${formatPeriodDate(endInput.value)}`;
  };
  const clearValidation = () => {
    validation.hidden = true;
    validation.textContent = "";
    startInput.removeAttribute("aria-invalid");
    endInput.removeAttribute("aria-invalid");
  };
  updateLabel();
  period?.addEventListener("toggle", () => {
    if (period.open) {
      period.dataset.originalStart = startInput.value;
      period.dataset.originalEnd = endInput.value;
      clearValidation();
      status.hidden = true;
    }
  });
  cancel?.addEventListener("click", () => {
    startInput.value = period.dataset.originalStart || startInput.value;
    endInput.value = period.dataset.originalEnd || endInput.value;
    clearValidation();
    period.open = false;
  });
  startInput.addEventListener("input", clearValidation);
  endInput.addEventListener("input", clearValidation);
  form.addEventListener("submit", event => {
    event.preventDefault();
    if (!startInput.value || !endInput.value || startInput.value > endInput.value) {
      validation.textContent = "Informe datas válidas e confirme que a data inicial não é posterior à final.";
      validation.hidden = false;
      startInput.setAttribute("aria-invalid", String(!startInput.value || startInput.value > endInput.value));
      endInput.setAttribute("aria-invalid", String(!endInput.value));
      return;
    }
    clearValidation();
    status.hidden = true;
    const apply = document.querySelector(".period-apply");
    apply.disabled = true;
    apply.textContent = "Aplicando…";
    loadExplanation();
  });
  document.querySelector("#understand-questions")?.addEventListener("click", event => {
    const button = event.target.closest("[data-analysis-id]");
    if (!button) return;
    selectedUnderstandAnalysis = button.dataset.analysisId;
    renderAnalysisAnswer(contributionData);
  });
}

export async function loadExplanation() {
  const requestId = ++explanationRequestId;
  const start = document.querySelector("#wealth-start-date").value;
  const end = document.querySelector("#wealth-end-date").value;
  const target = document.querySelector("#wealth-explanation");
  target.innerHTML = '<div class="empty">Calculando análise com o histórico registrado…</div>';
  try {
    const data = await portfolioApi.wealthExplanation(start, end);
    if (requestId !== explanationRequestId) return;
    document.querySelector("#wealth-start-date").value = data.period.start_date;
    document.querySelector("#wealth-end-date").value = data.period.end_date;
    const periodLabel = document.querySelector("#wealth-period-label");
    if (periodLabel) periodLabel.textContent = `${formatPeriodDate(data.period.start_date)} — ${formatPeriodDate(data.period.end_date)}`;
    const period = document.querySelector("#understand-period-disclosure");
    if (period) { period.dataset.originalStart = data.period.start_date; period.dataset.originalEnd = data.period.end_date; }
    if (period) period.open = false;
    const status = document.querySelector("#understand-period-status");
    if (status) { status.hidden = true; status.classList.remove("error"); }
    const domStarted = performance.now();
    renderExplanation(data);
    performance.measure("income:entender-dom-render", { start: domStarted, end: performance.now() });
  } catch (error) {
    if (requestId === explanationRequestId) {
      target.innerHTML = errorState(error.message);
      const period = document.querySelector("#understand-period-disclosure");
      const startInput = document.querySelector("#wealth-start-date");
      const endInput = document.querySelector("#wealth-end-date");
      if (period && period.dataset.originalStart && period.dataset.originalEnd) {
        startInput.value = period.dataset.originalStart;
        endInput.value = period.dataset.originalEnd;
        const label = document.querySelector("#wealth-period-label");
        if (label) label.textContent = `${formatPeriodDate(startInput.value)} — ${formatPeriodDate(endInput.value)}`;
      }
      const status = document.querySelector("#understand-period-status");
      if (status) {
        status.textContent = contributionData
          ? "Não foi possível atualizar o período. O intervalo anterior continua aplicado."
          : "Não foi possível carregar a análise para este período. Tente novamente.";
        status.classList.add("error");
        status.hidden = false;
      }
      if (period) period.open = true;
    }
  } finally {
    if (requestId === explanationRequestId) {
      const apply = document.querySelector(".period-apply");
      if (apply) { apply.disabled = false; apply.textContent = "Aplicar"; }
    }
  }
}

function formatPeriodDate(value) {
  const [year, month, day] = String(value).split("-");
  return year && month && day ? `${day}/${month}/${year}` : String(value || "");
}

function renderExplanation(data) {
  contributionData = data;
  renderPeriodSummary(data);
  renderQuestionChoices();
  renderAnalysisAnswer(data);
}

function renderPeriodSummary(data) {
  const target = document.querySelector("#wealth-period-summary");
  const summary = data.summary || {};
  const bridge = data.bridge || {};
  const quality = data.data_quality || {};
  const amount = value => value === null || value === undefined ? "Indisponível" : money(value, data.base_currency);
  const signed = value => value === null || value === undefined ? "Indisponível" : `${Number(value) > 0 ? "+" : Number(value) < 0 ? "−" : ""}${money(Math.abs(Number(value)), data.base_currency)}`;
  const changePct = summary.percentage_wealth_change === null ? "Indisponível" : percentage(Number(summary.percentage_wealth_change) * 100);
  const metrics = [
    ["Variação patrimonial", `${signed(summary.absolute_change)} · ${changePct}`, "Variação do saldo; não equivale necessariamente à rentabilidade."],
    ["Saldo inicial", amount(summary.opening_wealth)],
    ["Saldo final", amount(summary.closing_wealth)],
    ["Valorização dos ativos", signed(bridge.market_appreciation)],
    ["Renda fixa valorizada", signed(bridge.fixed_income_return), "Variação apurada no saldo; juros pagos não são adicionados novamente."],
    ["Rendimentos recebidos", signed(data.income_generated?.total)],
    ["Aquisições líquidas", signed(bridge.net_acquisitions)],
  ];
  const coverage = quality.valuation_complete ? "Valuation completo nas datas de abertura e encerramento." : `Valuation parcial · cobertura ${quality.valuation_coverage_percentage === null ? "indisponível" : percentage(Number(quality.valuation_coverage_percentage))}. Valores pendentes não foram tratados como zero.`;
  target.innerHTML = `<section class="card understand-summary-card"><div class="understand-summary-heading"><div><p class="eyebrow">${escapeChartText(data.period.start_date)} a ${escapeChartText(data.period.end_date)}</p><h2>Resumo do período</h2></div><span class="coverage-pill ${quality.valuation_complete ? "complete" : "partial"}">${quality.valuation_complete ? "Cobertura completa" : "Cobertura parcial"}</span></div><div class="understand-metrics">${metrics.map(([label, value, note], index) => `<div class="understand-metric ${index === 0 ? "primary" : ""}"><small>${label}</small><strong>${value}</strong>${note ? `<span>${note}</span>` : ""}</div>`).join("")}</div><p class="coverage">${coverage}</p></section>`;
}

function renderQuestionChoices() {
  const target = document.querySelector("#understand-questions");
  target.innerHTML = understandAnalyses.map((analysis, index) => `<button type="button" class="understand-question ${analysis.id === selectedUnderstandAnalysis ? "selected" : ""}" data-analysis-id="${analysis.id}" aria-pressed="${analysis.id === selectedUnderstandAnalysis}"><span>${String(index + 1).padStart(2, "0")}</span>${analysis.question}</button>`).join("");
}

function renderAnalysisAnswer(data) {
  const target = document.querySelector("#wealth-explanation");
  if (!target || !data) return;
  renderQuestionChoices();
  const selected = understandAnalyses.find(item => item.id === selectedUnderstandAnalysis) || understandAnalyses[0];
  const content = selected.render(data);
  target.innerHTML = `<article class="card understand-answer-card"><div class="understand-answer-heading"><p class="eyebrow">Análise ${String(understandAnalyses.indexOf(selected) + 1).padStart(2, "0")}</p><h2>${selected.question}</h2></div>${content}</article>`;
  bindAnswerControls();
}

function renderAssetContributionAnswer(data) {
  const quality = data.data_quality || {};
  const rows = buildContributionRows(data);
  const classSet = [...new Set(rows.map(row => row.asset_class))].sort((a, b) => (labels[a] || a).localeCompare(labels[b] || b, "pt-BR"));
  if (rankingClassFilter && !classSet.includes(rankingClassFilter)) rankingClassFilter = "";
  const visible = filterAndSortContributions(rows, contributionDirection, rankingClassFilter);
  const gains = visible.filter(row => row.value > 0);
  const losses = visible.filter(row => row.value < 0);
  const net = visible.reduce((total, row) => total + row.value, 0);
  const conclusion = visible.length ? `Maior ganho identificado: ${escapeChartText(gains[0]?.ticker || "nenhum")} (${signedMoney(gains[0]?.value || 0, data.base_currency)}). Maior perda: ${escapeChartText(losses[0]?.ticker || "nenhum")} (${signedMoney(losses[0]?.value || 0, data.base_currency)}).` : "Não há contribuições calculáveis para esta seleção.";
  const listedRows = (rankingShowAll ? visible : visible.slice(0, 10)).map((row, index) => `<details class="asset-ranking-row" ${expandedAsset === row.ticker ? "open" : ""} data-ranking-asset="${escapeChartText(row.ticker)}"><summary><span class="ranking-position">${index + 1}</span><span class="ranking-identity"><strong>${escapeChartText(row.ticker)}</strong><small>${labels[row.asset_class] || row.asset_class}${row.valuation_available ? "" : " · cobertura parcial"}</small></span><span class="ranking-bar"><i class="${row.value < 0 ? "negative" : "positive"}" style="width:${Math.max(3, Math.abs(row.value) / Math.max(1, ...visible.map(item => Math.abs(item.value))) * 100)}%"></i></span><strong class="ranking-value ${row.value < 0 ? "negative-text" : "positive-text"}">${signedMoney(row.value, data.base_currency)}</strong></summary><div class="asset-ranking-detail">${Object.entries(row.factors).filter(([, value]) => value !== 0).map(([factor, value]) => `<div><span>${factorLabels[factor] || factor}</span><strong>${signedMoney(value, data.base_currency)}</strong></div>`).join("") || `<p>Detalhamento não disponível para este ativo.</p>`}</div></details>`).join("");
  const unavailableRows = rows.filter(row => !row.contribution_available && (!rankingClassFilter || row.asset_class === rankingClassFilter));
  const unavailableCount = unavailableRows.length;
  const classes = classSet.map(assetClass => `<option value="${assetClass}" ${assetClass === rankingClassFilter ? "selected" : ""}>${labels[assetClass] || assetClass}</option>`).join("");
  const partial = !quality.valuation_complete || unavailableCount > 0;
  return `<p class="analysis-conclusion">${conclusion}</p><div class="analysis-totals"><div><small>Contribuições positivas apuradas</small><strong class="positive-text">${signedMoney(gains.reduce((sum, row) => sum + row.value, 0), data.base_currency)}</strong></div><div><small>Contribuições negativas apuradas</small><strong class="negative-text">${signedMoney(losses.reduce((sum, row) => sum + row.value, 0), data.base_currency)}</strong></div><div><small>Resultado líquido identificado</small><strong>${signedMoney(net, data.base_currency)}</strong></div></div><div class="analysis-filters"><label>Classe de ativo<select id="ranking-class-filter"><option value="">Todas as classes</option>${classes}</select></label><div class="segmented-control" role="group" aria-label="Filtrar contribuições"><button type="button" data-direction="ALL" aria-pressed="${contributionDirection === "ALL"}">Todos</button><button type="button" data-direction="GAINS" aria-pressed="${contributionDirection === "GAINS"}">Ganhos</button><button type="button" data-direction="LOSSES" aria-pressed="${contributionDirection === "LOSSES"}">Perdas</button></div><div class="metric-switch" role="group" aria-label="Métrica"><button type="button" class="active" aria-pressed="true">R$</button><button type="button" disabled title="O motor financeiro não calcula TWR individual por ativo.">%</button></div></div><p class="coverage metric-unavailable">% indisponível: o motor atual calcula TWR para a carteira e por classe, não por ativo. Nenhum percentual foi estimado.</p>${partial ? `<aside class="analysis-quality" role="status">Ranking parcial. ${unavailableCount} ativo(s) sem contribuição calculável foram separados do resultado. Cobertura do valuation: ${quality.valuation_coverage_percentage === null ? "indisponível" : percentage(Number(quality.valuation_coverage_percentage))}.</aside>${unavailableRows.length ? `<details class="analysis-evidence"><summary>Ver ativos sem contribuição calculável</summary><div class="bridge-answer-children">${unavailableRows.map(row => `<div><span>${escapeChartText(row.ticker)} · ${labels[row.asset_class] || row.asset_class}</span><strong>Indisponível</strong></div>`).join("")}</div></details>` : ""}` : ""}<div class="asset-ranking">${listedRows || `<div class="empty">Sem contribuições para os filtros selecionados.</div>`}</div>${visible.length > 10 ? `<button type="button" id="ranking-expand" class="secondary ranking-expand">${rankingShowAll ? "Mostrar os 10 principais" : `Ver todos os ${visible.length} investimentos`}</button>` : ""}<details class="analysis-evidence"><summary>Como esta contribuição é calculada?</summary><p>O ranking soma valorização de mercado, variação apurada da renda fixa, ajustes de valuation e rendimentos atribuídos ao ativo. Compras e vendas não entram como ganho. O resultado não é rentabilidade percentual.</p></details>`;
}

function renderWealthBridgeAnswer(data) {
  const summary = data.summary || {};
  const quality = data.data_quality || {};
  const rows = (data.components || []).filter(item => item.component_type !== "UNEXPLAINED" || Number(item.signed_amount) !== 0);
  const bridge = rows.map(item => {
    const marketValuation = item.component_type === "MARKET_VALUATION";
    const totalValue = marketValuation ? movementIndicator(item.signed_amount, data.base_currency) : signedMoney(item.signed_amount, data.base_currency);
    const children = item.children?.length
      ? `<div class="bridge-answer-children">${[...item.children].sort((a, b) => Math.abs(Number(b.signed_amount)) - Math.abs(Number(a.signed_amount))).map(child => `<div><span>${escapeChartText(child.ticker || child.label || "Ativo")}${child.valuation_available === false ? " · valuation pendente" : ""}</span><strong>${marketValuation ? movementIndicator(child.signed_amount, data.base_currency) : signedMoney(child.signed_amount, data.base_currency)}</strong></div>`).join("")}</div>`
      : "";
    return `<details class="bridge-answer-row"><summary><span>${item.label}</span><strong>${totalValue}</strong></summary>${children}</details>`;
  }).join("");
  const residual = Number(data.reconciliation?.unexplained_change || 0);
  const conclusion = `O saldo de ativos ${Number(summary.absolute_change) >= 0 ? "aumentou" : "diminuiu"} ${signedMoney(summary.absolute_change, data.base_currency)} no período.`;
  return `<p class="analysis-conclusion">${conclusion}</p><div class="wealth-bridge-answer"><div class="bridge-answer-total"><span>Saldo inicial</span><strong>${money(summary.opening_wealth, data.base_currency)}</strong></div>${bridge}<div class="bridge-answer-total"><span>Saldo final</span><strong>${money(summary.closing_wealth, data.base_currency)}</strong></div></div><p class="coverage">${quality.explanation_coverage_percentage === null ? "Cobertura da reconciliação indisponível." : `Cobertura da explicação: ${percentage(Number(quality.explanation_coverage_percentage))}.`} ${residual ? `Variação sem causa identificada: ${signedMoney(residual, data.base_currency)}.` : "Os componentes conhecidos reconciliam a variação."}</p><details class="analysis-evidence"><summary>Limites desta reconciliação</summary><p>Valuation parcial: ${percentage(Number(quality.valuation_coverage_percentage || 0))}. Efeito cambial detalhado não está disponível neste relatório. ${quality.unconverted_event_count ? `${quality.unconverted_event_count} evento(s) não foram convertidos para a moeda-base.` : ""}</p></details>`;
}

function movementIndicator(value, currency) {
  const amount = Number(value);
  const direction = amount > 0 ? "up" : amount < 0 ? "down" : "flat";
  const description = amount > 0 ? "Valorização positiva" : amount < 0 ? "Valorização negativa" : "Sem variação";
  const path = direction === "up" ? "M5 17 17 5M7 5h10v10" : direction === "down" ? "M5 7 17 19M17 9v10H7" : "M5 12h14";
  return `<span class="movement-value movement-${direction}" aria-label="${description}"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="${path}" /></svg><span>${money(Math.abs(amount), currency)}</span></span>`;
}

function renderIncomeAnswer(data) {
  const items = (data.income_generated?.items || []).map(item => ({ ...item, value: Number(item.signed_amount) })).sort((a, b) => b.value - a.value || String(a.ticker).localeCompare(String(b.ticker), "pt-BR"));
  const classes = [...new Set(items.map(item => item.asset_class))].sort();
  if (incomeClassFilter && !classes.includes(incomeClassFilter)) incomeClassFilter = "";
  const filtered = items.filter(item => !incomeClassFilter || item.asset_class === incomeClassFilter);
  const rows = filtered.map((item, index) => `<div class="income-ranking-row"><span class="ranking-position">${index + 1}</span><span class="ranking-identity"><strong>${escapeChartText(item.ticker)}</strong><small>${labels[item.asset_class] || item.asset_class} · ${incomeEventLabels[item.event_type] || item.event_type}</small></span><strong class="positive-text">${money(item.value, data.base_currency)}</strong></div>`).join("");
  return `<p class="analysis-conclusion">${filtered.length ? `${escapeChartText(filtered[0].ticker)} gerou mais renda no período (${money(filtered[0].value, data.base_currency)}).` : "Nenhum rendimento suportado foi registrado para estes filtros no período."}</p><div class="analysis-filters"><label>Classe de ativo<select id="income-class-filter"><option value="">Todas as classes</option>${classes.map(assetClass => `<option value="${assetClass}" ${assetClass === incomeClassFilter ? "selected" : ""}>${labels[assetClass] || assetClass}</option>`).join("")}</select></label></div><div class="analysis-totals"><div><small>Total de rendimentos registrados</small><strong>${money(filtered.reduce((sum, item) => sum + item.value, 0), data.base_currency)}</strong></div><div><small>Eventos atribuídos</small><strong>${filtered.length}</strong></div></div><div class="income-ranking">${rows || `<div class="empty">Sem rendimentos atribuídos a esta classe.</div>`}</div><details class="analysis-evidence"><summary>Eventos incluídos e limite do serviço</summary><p>Dividendos, juros sobre capital próprio e rendimentos de FIIs registrados no ledger e convertidos para ${data.base_currency}. Juros de renda fixa ainda não são expostos como rendimento por este serviço e, por isso, não entram neste ranking.</p></details>`;
}

function renderFixedIncomeAnswer(data) {
  const rows = buildContributionRows(data).filter(row => row.asset_class === "FIXED_INCOME");
  const available = rows.filter(row => row.contribution_available && Number.isFinite(Number(row.factors.FIXED_INCOME_ACCRUAL))).sort((left, right) => Number(right.factors.FIXED_INCOME_ACCRUAL) - Number(left.factors.FIXED_INCOME_ACCRUAL));
  const unavailable = rows.filter(row => !row.contribution_available);
  const total = data.bridge?.fixed_income_return;
  const components = available.map((row, index) => { const value = Number(row.factors.FIXED_INCOME_ACCRUAL); return `<details class="income-ranking-row fixed-income-ranking"><summary><span class="ranking-position">${index + 1}</span><span class="ranking-identity"><strong>${escapeChartText(row.ticker)}</strong><small>${escapeChartText(row.name)}</small></span><strong class="${value < 0 ? "negative-text" : "positive-text"}">${signedMoney(value, data.base_currency)}</strong></summary><div class="asset-ranking-detail"><div><span>Variação apurada do saldo</span><strong>${signedMoney(value, data.base_currency)}</strong></div>${row.factors.PAID_INCOME ? `<div><span>Rendimento pago (informação separada)</span><strong>${signedMoney(row.factors.PAID_INCOME, data.base_currency)}</strong></div>` : ""}</div></details>`; }).join("");
  const status = unavailable.length ? `${unavailable.length} posição(ões) não puderam ser apuradas por valuation incompleto.` : "";
  return `<div class="fixed-income-big-number"><small>Variação apurada da renda fixa</small><strong>${total === null || total === undefined ? "Indisponível" : signedMoney(total, data.base_currency)}</strong><p>Valor da reconciliação existente; aplicações e resgates são tratados à parte.</p></div><p class="analysis-conclusion">${available.length ? `${available.length} investimento(s) de renda fixa com valuation por ativo apurado no período.` : "Não há base de valuation por investimento suficiente para detalhar este período."}</p>${status ? `<aside class="analysis-quality">${status}</aside>` : ""}<div class="income-ranking">${components || `<div class="empty">Sem posições de renda fixa com valuation detalhado.</div>`}</div><details class="analysis-evidence"><summary>O que esta análise distingue</summary><p>O valor em destaque é o componente da renda fixa calculado na reconciliação existente. O serviço não distingue juros pagos de juros incorporados nem marcação a mercado e amortizações por investimento; os juros pagos são apresentados em separado quando há evento registrado e não são somados novamente ao Big Number.</p></details>`;
}

function bindAnswerControls() {
  document.querySelector("#ranking-class-filter")?.addEventListener("change", event => { rankingClassFilter = event.target.value; renderAnalysisAnswer(contributionData); });
  document.querySelector("#income-class-filter")?.addEventListener("change", event => { incomeClassFilter = event.target.value; renderAnalysisAnswer(contributionData); });
  document.querySelectorAll("[data-direction]").forEach(button => button.addEventListener("click", () => { contributionDirection = button.dataset.direction; rankingShowAll = false; renderAnalysisAnswer(contributionData); }));
  document.querySelector("#ranking-expand")?.addEventListener("click", () => { rankingShowAll = !rankingShowAll; renderAnalysisAnswer(contributionData); });
  document.querySelectorAll("[data-ranking-asset]").forEach(row => row.addEventListener("toggle", () => { if (row.open) expandedAsset = row.dataset.rankingAsset; }));
}

function signedMoney(value, currency = "BRL") {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "Indisponível";
  const amount = Number(value);
  return `${amount > 0 ? "+" : amount < 0 ? "−" : ""}${money(Math.abs(amount), currency)}`;
}

const factorLabels = { MARKET_VALUATION: "Valorização de mercado", FIXED_INCOME_ACCRUAL: "Variação da renda fixa", VALUATION_ADJUSTMENTS: "Ajustes de valuation", PAID_INCOME: "Rendimentos recebidos" };
const incomeEventLabels = { DIVIDEND: "Dividendo", INTEREST_ON_EQUITY: "JCP", FII_INCOME: "Rendimento de FII", FIXED_INCOME_INTEREST: "Juros de renda fixa" };

function buildContributionRows(data) {
  const assetRows = new Map();
  for (const component of data.components || []) {
    if (["NET_ACQUISITIONS", "UNEXPLAINED"].includes(component.component_type)) continue;
    for (const child of component.children || []) {
      const key = child.ticker || child.label || "Sem identificação";
      const row = assetRows.get(key) || { name: child.label || key, ticker: child.ticker || key, asset_class: child.asset_class || "OTHER", factors: {}, valuation_available: true };
      row.factors[component.component_type] = (row.factors[component.component_type] || 0) + Number(child.signed_amount || 0);
      row.valuation_available &&= child.valuation_available !== false;
      assetRows.set(key, row);
    }
  }
  for (const income of data.income_generated?.items || []) {
    const key = income.ticker || income.label || "Sem identificação";
    const row = assetRows.get(key) || { name: income.label || key, ticker: income.ticker || key, asset_class: income.asset_class || "OTHER", factors: {}, valuation_available: true };
    row.factors.PAID_INCOME = (row.factors.PAID_INCOME || 0) + Number(income.signed_amount || 0);
    assetRows.set(key, row);
  }
  return [...assetRows.values()].map(row => ({ ...row, value: Object.values(row.factors).reduce((sum, value) => sum + value, 0), contribution_available: row.valuation_available }));
}

function filterAndSortContributions(rows, direction = "ALL", assetClass = "") {
  return rows
    .filter(row => row.contribution_available && (!assetClass || row.asset_class === assetClass))
    .filter(row => direction === "ALL" || (direction === "GAINS" && row.value > 0) || (direction === "LOSSES" && row.value < 0))
    .sort((a, b) => {
      const order = direction === "GAINS" ? b.value - a.value : direction === "LOSSES" ? a.value - b.value : Math.abs(b.value) - Math.abs(a.value);
      return order || a.ticker.localeCompare(b.ticker, "pt-BR");
    });
}

function escapeChartText(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
}
