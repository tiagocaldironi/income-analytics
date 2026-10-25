import { assetClassLabel } from "../shared/asset-class-labels.js";

const escape = value => String(value ?? "").replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
const currency = (value, code = "BRL") => {
  const numeric = Number(value || 0);
  if (numeric !== 0 && Math.abs(numeric) < 1e-12) return `${escape(value)} ${escape(code)}`;
  return new Intl.NumberFormat("pt-BR", {style: "currency", currency: code, maximumFractionDigits: 12}).format(numeric);
};
const percent = value => value == null ? "—" : `${(Number(value) * 100).toLocaleString("pt-BR", {maximumFractionDigits: 2})}%`;
const quantity = value => {
  let text = String(value);
  if (/e/i.test(text)) {
    const [mantissa, exponent] = text.toLowerCase().split("e");
    const [whole, fraction = ""] = mantissa.split(".");
    const digits = whole + fraction;
    const point = whole.length + Number(exponent);
    text = point <= 0 ? "0." + "0".repeat(-point) + digits : point >= digits.length ? digits + "0".repeat(point - digits.length) : digits.slice(0, point) + "." + digits.slice(point);
  }
  const match = text.match(/^(\d+)(?:\.(\d+))?$/);
  if (!match) return "—";
  const fraction = (match[2] || "").replace(/0+$/, "");
  return BigInt(match[1]).toLocaleString("pt-BR") + (fraction ? `,${fraction}` : "");
};
const reasons = {
  NEEDS_ASSET_STRATEGY: "Defina a composição dos ativos desta classe na sua estratégia.",
  NEEDS_APPLICATION_TERMS: "Informe o mínimo e o incremento de aplicação deste produto.",
  MISSING_PRICE: "Sem cotação observada disponível para compra.",
  STALE_PRICE: "A cotação está fora da política de validade do plano.",
  FUTURE_PRICE: "A referência do preço é futura e não pode ser utilizada.",
  MISSING_FX: "Sem câmbio disponível para converter a compra.",
  STALE_FX: "A referência de câmbio está fora da política de validade.",
  INACTIVE_ASSET: "O ativo está inativo no cadastro da carteira.",
  UNSUPPORTED_MARKET: "As condições de negociação deste mercado ainda não são suportadas.",
};

function purchaseReason(item) {
  if (item.reason === "GLOBAL_DISTANCE_REDUCED") return "No conjunto, estas compras reduzem o desvio global em relação à estratégia.";
  if (item.reason === "ASSET_DISTANCE_REDUCED") return "O plano aproxima os objetivos por ativo sem piorar a distribuição das classes.";
  if (item.reason === "GLOBAL_STRATEGY_PRESERVED") return "O plano mantém a aderência à estratégia e aumenta o valor investido.";
  return "Compra compatível com os objetivos e as restrições do plano avaliado.";
}

function residualExplanation(plan) {
  if (Number(plan.residual_amount) <= 0) return "Não há saldo residual.";
  const codes = new Set(plan.residual_reasons || []);
  const messages = [];
  if (codes.has("SEARCH_LIMIT")) messages.push("A busca atingiu seu limite de avaliação; este saldo não é considerado inevitável.");
  if (codes.has("MINIMUM_EXCEEDS_BALANCE")) messages.push("Para parte dos ativos, uma unidade ou lote mínimo supera o saldo disponível, incluindo os custos informados.");
  if (codes.has("GLOBAL_STRATEGY_LIMIT")) messages.push("As compras que ainda cabem não melhoram a aderência global nas alternativas avaliadas.");
  if (["MISSING_PRICE", "STALE_PRICE", "FUTURE_PRICE", "MISSING_FX", "STALE_FX"].some(code => codes.has(code))) messages.push("Outros ativos dependem de cotação ou câmbio válidos; nenhum preço foi presumido.");
  if (codes.has("NEEDS_ASSET_STRATEGY")) messages.push("Classes sem composição por ativo não geram escolhas automáticas.");
  if (["NEEDS_APPLICATION_TERMS", "UNSUPPORTED_MARKET", "INACTIVE_ASSET"].some(code => codes.has(code))) messages.push("Restrições de negociação também limitam os ativos elegíveis.");
  return messages.join(" ") || "Nenhuma compra adicional viável que melhore a estratégia foi encontrada nas alternativas avaliadas.";
}

export function renderExecutablePlan(plan, comparisonMarkup = "") {
  const base = plan.base_currency;
  const blocked = (plan.blocked || []).map(item => `<li><b>${escape(item.ticker || assetClassLabel(item.asset_class))}</b> — ${escape(reasons[item.reason] || "Dados insuficientes.")} ${Number(item.reserved_amount) > 0 ? `<span>${currency(item.reserved_amount, base)} a aguardar dados.</span>` : ""}</li>`).join("");
  const rules = renderTradingRules(plan.instruments || [], base);
  if (plan.status === "INSUFFICIENT") return `<section class="card simulation-executable"><h2>A avaliação da carteira está incompleta</h2><p>Atualize as cotações e o câmbio das posições antes de calcular quantidades. Um patrimônio incompleto não permite medir os desvios com segurança.</p><p>Nenhuma compra foi sugerida. ${currency(plan.budget, base)} aguardam dados.</p>${blocked ? `<ul>${blocked}</ul>` : ""}</section>${rules}`;
  return `<section class="simulation-hero"><p class="eyebrow">Seu plano de aporte</p><div class="simulation-hero-grid"><div><span>Orçamento</span><strong>${currency(plan.budget, base)}</strong></div><div><span>Total estimado das compras</span><strong>${currency(plan.total_estimated, base)}</strong><small>Inclui ${currency(plan.estimated_costs, base)} de custos estimados e arredondamento.</small></div><div><span>Saldo restante</span><strong>${currency(plan.remaining_amount, base)}</strong><small>Sem operações registradas ou ordens enviadas.</small></div></div></section>${comparisonMarkup}<section class="card simulation-executable"><header><p class="eyebrow">Quantidades negociáveis</p><h2>Plano estimado de compras</h2><p>Preços de referência datados, sujeitos à execução da corretora. Esta simulação é educacional.</p></header><div class="simulation-order-list">${plan.orders.length ? plan.orders.map(item => `<article class="simulation-order"><header><div><h3>${escape(item.ticker)}</h3><p>${escape(item.label)} · ${escape(assetClassLabel(item.asset_class))} · ${escape(item.market)}</p></div><strong>${quantity(item.quantity)} ${item.asset_class === "FIXED_INCOME" ? "unidades do produto" : "unidades"}</strong></header><dl><div><dt>Preço unitário utilizado</dt><dd>${currency(item.unit_price, item.currency)}</dd></div><div><dt>Referência do preço</dt><dd>${escape(item.price_timestamp || item.price_date)} · ${escape(item.price_source)}</dd><small>${Number(item.price_age_days) ? `${Number(item.price_age_days)} dia(s) de defasagem` : "Referência do dia; não é cotação em tempo real"}</small></div><div><dt>Compra estimada em ${escape(base)}</dt><dd>${currency(item.estimated_total, base)}</dd><small>${item.costs_known ? "Custos informados pelo usuário" : "Custos da corretora não informados"}</small></div><div><dt>Participação na carteira</dt><dd>${percent(item.weight_before)} → ${percent(item.weight_after)}</dd><small>Objetivo: ${percent(item.target_weight)}</small></div>${item.currency !== base ? `<div><dt>Câmbio utilizado</dt><dd>1 ${escape(item.currency)} = ${currency(item.fx_rate, base)}</dd><small>Referência: ${escape(item.fx_date)} · compra ${currency(item.native_amount, item.currency)}</small></div>` : ""}</dl><p class="simulation-order-reason">${purchaseReason(item)} Quantidade em incrementos de ${quantity(item.quantity_step)}.</p></article>`).join("") : `<p>Nenhuma compra elegível cabe no orçamento e melhora o objetivo nas condições atuais.</p>`}</div><div class="simulation-plan-balance" role="status"><p><b>Saldo residual: ${currency(plan.residual_amount, base)}</b></p><p>${residualExplanation(plan)}</p>${Number(plan.unavailable_budget) > 0 ? `<p><b>Orçamento aguardando dados: ${currency(plan.unavailable_budget, base)}</b>. Esse valor foi reservado para manter a estratégia; não foi redistribuído a outros ativos.</p>` : ""}</div>${blocked ? `<details class="simulation-blocked" open><summary>Ativos ou classes não simuláveis</summary><ul>${blocked}</ul><a href="#estrategia" data-navigate>Revisar estratégia</a></details>` : ""}<p class="field-help">O saldo elegível foi reavaliado após os arredondamentos. Não incluímos ativos fora da estratégia para consumir o orçamento. Custos não informados, spread e condições específicas da corretora podem alterar a viabilidade.</p></section>${rules}`;
}

function renderTradingRules(instruments, base) {
  if (!instruments.length) return "";
  return `<details class="card simulation-trading-rules"><summary>Regras de negociação e custos</summary><p>Condições desta simulação, sem alterar a estratégia. Confira as regras com sua corretora e use “Atualizar cenário” após editar. A política aceita preços de até 7 dias corridos, cripto de até 1 dia e câmbio de até 5 dias.</p><div class="simulation-rule-list">${instruments.map(item => {
    const foreign = ["INTERNATIONAL", "INTERNATIONAL_ETF", "US_REIT"].includes(item.asset_class);
    return `<fieldset data-trading-rule="${escape(item.ticker)}" data-asset-class="${escape(item.asset_class)}"><legend>${escape(item.ticker)} · ${escape(assetClassLabel(item.asset_class))}</legend>${foreign ? `<label class="simulation-rule-check"><input type="checkbox" data-rule="fractional_supported" ${item.fractional_supported ? "checked" : ""}>Minha corretora permite frações deste ativo</label>` : ""}<div class="simulation-rule-fields">${foreign || item.asset_class === "CRYPTO" ? `<label>Casas decimais<input type="number" data-rule="quantity_precision" min="0" max="12" step="1" value="${Number(item.quantity_precision)}"></label>` : ""}<label>Incremento de quantidade<input type="number" data-rule="quantity_step" min="0.000000000001" step="any" value="${escape(item.quantity_step)}"></label><label>Quantidade mínima<input type="number" data-rule="minimum_quantity" min="0" step="any" value="${escape(item.minimum_quantity || item.quantity_step)}"></label><label>Mínimo de compra em ${escape(item.currency)}<input type="number" data-rule="minimum_amount" min="0" step="any" value="${escape(item.minimum_amount)}"></label>${item.asset_class === "FIXED_INCOME" ? `<label>Incremento de aplicação em ${escape(item.currency)}<input type="number" data-rule="amount_increment" min="0.00000001" step="any" placeholder="Informe o incremento" value="${Number(item.amount_increment) > 0 ? escape(item.amount_increment) : ""}"></label>` : ""}<label>Custo fixo por compra em ${escape(base)}<input type="number" data-rule="fixed_fee_base" min="0" step="0.01" value="${escape(item.fixed_fee_base)}"></label><label>Custos proporcionais (%)<input type="number" data-rule="fee_percent" min="0" max="100" step="0.000001" value="${Number(item.fee_rate) * 100}"></label></div><label class="simulation-rule-check"><input type="checkbox" data-rule="costs_known" ${item.costs_known ? "checked" : ""}>Informei os custos conhecidos desta compra</label>${foreign ? "<small>Sem confirmação, serão utilizadas apenas quantidades inteiras.</small>" : ""}</fieldset>`;
  }).join("")}</div><p>As condições são mantidas apenas enquanto esta tela está aberta. Nenhuma regra da corretora é presumida como verificada.</p></details>`;
}

export function collectTradingRules(target) {
  return Object.fromEntries([...target.querySelectorAll("[data-trading-rule]")].map(fieldset => {
    const values = {};
    fieldset.querySelectorAll("[data-rule]").forEach(input => {
      if (input.type === "checkbox") values[input.dataset.rule] = input.checked;
      else if (input.value !== "") values[input.dataset.rule] = input.value;
    });
    if (values.fee_percent !== undefined) {
      values.fee_rate = (Number(values.fee_percent) / 100).toFixed(8);
      delete values.fee_percent;
    }
    return [fieldset.dataset.tradingRule, values];
  }));
}

export function bindTradingRules(target) {
  target.querySelectorAll("[data-trading-rule]").forEach(fieldset => {
    const fractional = fieldset.querySelector('[data-rule="fractional_supported"]');
    const precision = fieldset.querySelector('[data-rule="quantity_precision"]');
    const step = fieldset.querySelector('[data-rule="quantity_step"]');
    const minimum = fieldset.querySelector('[data-rule="minimum_quantity"]');
    const update = () => {
      const previousStep = step?.value;
      if (step) step.value = fractional && !fractional.checked ? "1" : String(10 ** -Number(precision?.value || 0));
      if (minimum && Number(minimum.value) === Number(previousStep)) minimum.value = step.value;
    };
    fractional?.addEventListener("change", update);
    precision?.addEventListener("change", update);
  });
}
