import { portfolioApi } from "../api.js";
import { assetClassLabel } from "../shared/asset-class-labels.js";
import { friendlyError, money } from "../shared/ui.js";

const percent = value => value == null ? "—" : `${(Number(value) * 100).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 2 })}%`;
const points = value => value == null ? "—" : `${Number(value * 100).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 2 })} p.p.`;
const width = value => `${Math.max(0, Math.min(100, Number(value || 0) * 100))}%`;
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);

let latestResult = null;
let strategy = null;

function strategyContext() {
  if (!strategy) return "";
  return `<div class="simulation-strategy-context"><span>Estratégia utilizada</span><div>${strategy.comparisons.map(item => `<span><b>${assetClassLabel(item.asset_class)}</b>${percent(item.target_weight)}</span>`).join("")}</div></div>`;
}

export function renderSetup(target, { noStrategy = false } = {}) {
  target.innerHTML = `<section class="simulation-intent card"><p class="eyebrow">O que você quer testar?</p><div class="simulation-intent-main"><span class="simulation-intent-icon" aria-hidden="true">＋</span><div><h2>Novo aporte</h2><p>Tenho dinheiro novo para investir.</p></div><span class="simulation-active-label">Ativo</span></div><p class="simulation-future">Rebalanceamento e mudanças livres estarão disponíveis em uma etapa futura.</p></section><section class="simulation-config card"><div><p class="eyebrow">Quanto você quer simular?</p><label class="simulation-amount" for="simulation-amount"><span>R$</span><input id="simulation-amount" inputmode="decimal" type="number" min="0.01" step="0.01" placeholder="0,00" aria-describedby="simulation-amount-error"></label><p id="simulation-amount-error" class="simulation-field-error" role="alert"></p><div class="simulation-chips" aria-label="Atalhos de valor">${[1000, 5000, 10000, 50000].map(value => `<button type="button" class="secondary" data-simulation-amount="${value}">${money(value).replace(",00", "")}</button>`).join("")}</div></div><div><p class="eyebrow">Como você quer distribuir este aporte?</p><label class="simulation-mode selected"><input type="radio" name="simulation-mode" value="STRATEGY_GUIDED" checked><span><b>Aproximar da minha estratégia</b><small>Usa os objetivos cadastrados para aproximar a carteira resultante, sem vender posições.</small></span></label><label class="simulation-mode disabled" aria-disabled="true"><input type="radio" disabled><span><b>Manter minha distribuição atual</b><small>Disponível em uma etapa futura.</small></span></label>${noStrategy ? `<div class="simulation-no-strategy"><p>Você ainda não definiu uma estratégia por classe.</p><a href="#estrategia" data-navigate>Definir estratégia</a></div>` : strategyContext()}</div><button id="run-simulation" type="button" ${noStrategy ? "disabled" : ""}>Simular aporte</button></section><div id="simulation-result" aria-live="polite"></div>`;
  bindSetup(target);
}

function bindSetup(target) {
  const input = target.querySelector("#simulation-amount");
  target.querySelectorAll("[data-simulation-amount]").forEach(button => button.addEventListener("click", () => {
    input.value = button.dataset.simulationAmount;
    if (latestResult) run(target, button);
  }));
  target.querySelector("#run-simulation")?.addEventListener("click", event => run(target, event.currentTarget));
}

const loadingResult = () => `<section class="simulation-loading card" aria-busy="true"><span></span><span></span><span></span></section>`;

async function run(target, button) {
  const input = target.querySelector("#simulation-amount");
  const error = target.querySelector("#simulation-amount-error");
  const amount = Number(input.value);
  if (!Number.isFinite(amount) || amount <= 0) {
    error.textContent = "Informe um valor maior que zero.";
    input.focus();
    return;
  }
  error.textContent = "";
  const result = target.querySelector("#simulation-result");
  result.innerHTML = loadingResult();
  const original = button.textContent;
  button.disabled = true;
  if (button.id === "run-simulation") button.textContent = latestResult ? "Atualizando…" : "Simulando…";
  try {
    latestResult = await portfolioApi.simulateContribution({ amount: input.value, mode: "STRATEGY_GUIDED", include_asset_distribution: true });
    result.innerHTML = renderResult(latestResult);
  } catch (requestError) {
    result.innerHTML = `<div class="simulation-error card" role="alert"><b>Não foi possível calcular este cenário.</b><p>${escapeHtml(friendlyError(requestError))}</p></div>`;
  } finally {
    button.disabled = false;
    button.textContent = button.id === "run-simulation" && latestResult ? "Atualizar cenário" : original;
  }
}

function issueMessage(issues = []) {
  if (issues.includes("MISSING_FX")) return "Não foi possível converter uma ou mais posições em moeda estrangeira para BRL.";
  return "Não foi possível simular esta carteira de forma consistente porque faltam dados de avaliação para algumas posições.";
}

export function renderResult(data) {
  if (data.status !== "COMPLETE") return `<section class="simulation-insufficient card"><h2>Não foi possível montar o cenário</h2><p>${issueMessage(data.issues)}</p></section>`;
  const scenario = data.scenario;
  const comparison = data.comparison;
  const contributions = new Map(scenario.class_allocations.map(item => [item.asset_class, item]));
  const changes = [...comparison.class_changes].sort((a, b) => Math.abs(Number(b.weight_change_pp || 0)) - Math.abs(Number(a.weight_change_pp || 0)));
  const change = Number(comparison.strategy_distance_change || 0);
  const movement = `${points(Math.abs(change))} ${change <= 0 ? "mais próximo" : "mais distante"} da estratégia cadastrada`;
  return `<section class="simulation-hero"><p class="eyebrow">Seu cenário</p><div class="simulation-hero-grid"><div><span>Aporte</span><strong>${money(scenario.contribution_amount)}</strong></div><div><span>Patrimônio investido</span><strong>${money(comparison.wealth_before)} <i>→</i> ${money(comparison.invested_wealth_after)}</strong></div><div><span>Distância da estratégia</span><strong>${percent(comparison.strategy_distance_before)} <i>→</i> ${percent(comparison.strategy_distance_after)}</strong><small>${movement}</small></div></div></section>${renderClassComparison(changes)}${renderTopChanges(changes)}${renderDistribution(scenario, contributions)}${renderExplorer(changes, contributions)}`;
}

function renderClassComparison(changes) {
  return `<section class="card simulation-comparison"><div class="simulation-section-heading"><div><p class="eyebrow">Hoje → Cenário → Objetivo</p><h2>Como a composição ficaria</h2></div><div class="simulation-legend"><span class="today">Hoje</span><span class="scenario">Cenário</span><span class="target">Objetivo</span></div></div><div class="simulation-bullets">${changes.map(item => `<div class="simulation-bullet"><div><b>${assetClassLabel(item.asset_class)}</b><span>${percent(item.weight_before)} → <strong>${percent(item.weight_after)}</strong> → ${percent(item.target_weight)}</span></div><div class="simulation-track"><span class="simulation-fill" style="width:${width(item.weight_after)}"></span><i class="simulation-today" style="left:${width(item.weight_before)}"></i><i class="simulation-target" style="left:${width(item.target_weight)}"></i></div></div>`).join("")}</div></section>`;
}

function renderTopChanges(changes) {
  return `<section class="card simulation-changes"><p class="eyebrow">O que muda neste cenário?</p><div>${changes.slice(0, 5).map(item => `<article><b>${assetClassLabel(item.asset_class)}</b><span>${percent(item.weight_before)} → ${percent(item.weight_after)}</span><strong>${points(item.weight_change_pp)}</strong></article>`).join("")}</div></section>`;
}

function distributionStatus(item) {
  if (item.asset_distribution_status === "NEEDS_USER_DISTRIBUTION") return `<p>Sua estratégia define o objetivo da classe, mas não como esse valor deve ser distribuído entre os ativos.</p><dl><div><dt>Destinado à classe</dt><dd>${money(item.amount)}</dd></div><div><dt>Distribuído entre ativos</dt><dd>${money(item.asset_distributed_amount)}</dd></div><div><dt>A definir dentro da classe</dt><dd>${money(item.undistributed_within_class)}</dd></div></dl>`;
  if (item.asset_distribution_status === "INCOMPLETE_OR_INVALID_POLICY") return `<p>Não foi possível distribuir automaticamente este valor entre os ativos porque a composição-alvo da classe está incompleta.</p><a href="#estrategia" data-navigate>Revisar estratégia</a>`;
  return `<p>Distribuição simulada usando os objetivos dos ativos desta classe.</p>`;
}

function renderAssetRows(item) {
  if (!item.asset_allocations?.length) return "";
  return `<div class="simulation-assets">${item.asset_allocations.map(asset => `<div><b>${escapeHtml(asset.asset_label)}</b><span>${percent(asset.weight_before_in_class)} → <strong>${percent(asset.weight_after_in_class)}</strong> → ${percent(asset.target_weight_in_class)}</span><em>${money(asset.amount)}</em></div>`).join("")}</div>`;
}

function renderDistribution(scenario, contributions) {
  const items = [...contributions.values()].sort((a, b) => Number(b.amount) - Number(a.amount));
  const max = Math.max(...items.map(item => Number(item.amount)), 1);
  return `<section class="card simulation-distribution"><p class="eyebrow">Como o aporte seria distribuído?</p><h2>${money(scenario.contribution_amount)} entre as classes</h2><div class="simulation-distribution-list">${items.map(item => `<details><summary><span><b>${assetClassLabel(item.asset_class)}</b><i style="width:${Number(item.amount) / max * 100}%"></i></span><strong>${money(item.amount)}</strong></summary><div class="simulation-class-detail">${distributionStatus(item)}${renderAssetRows(item)}</div></details>`).join("")}</div>${Number(scenario.unallocated_amount) > 0 ? `<div class="simulation-residual"><b>Não distribuído</b><strong>${money(scenario.unallocated_amount)}</strong><p>Parte do valor não pôde ser distribuída dentro das regras deste cenário.</p></div>` : ""}</section>`;
}

function renderExplorer(changes, contributions) {
  return `<details class="card simulation-explorer"><summary>Ver detalhes do cenário</summary><div class="simulation-explorer-list">${changes.map(item => { const allocation = contributions.get(item.asset_class); return `<details><summary><b>${assetClassLabel(item.asset_class)}</b><span>${percent(item.weight_before)} → ${percent(item.weight_after)} · aporte ${money(allocation?.amount || 0)}</span></summary><div><dl><div><dt>Hoje</dt><dd>${percent(item.weight_before)}</dd></div><div><dt>Cenário</dt><dd>${percent(item.weight_after)}</dd></div><div><dt>Objetivo</dt><dd>${percent(item.target_weight)}</dd></div><div><dt>Mudança</dt><dd>${points(item.weight_change_pp)}</dd></div></dl>${allocation ? distributionStatus(allocation) + renderAssetRows(allocation) : `<p>Esta classe muda por diluição e não recebe aporte neste cenário.</p>`}</div></details>`; }).join("")}</div></details>`;
}

export async function bindSimulation() {
  const target = document.querySelector("#simulation-experience");
  if (!target) return;
  latestResult = null;
  try {
    strategy = await portfolioApi.allocationAnalysis();
    renderSetup(target);
  } catch (error) {
    strategy = null;
    renderSetup(target, { noStrategy: String(error?.message || error).toLowerCase().includes("política") });
  }
}
