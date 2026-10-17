import { portfolioApi } from "../api.js";
import { friendlyError, money } from "../shared/ui.js";
import { assetClassLabel } from "../shared/asset-class-labels.js";
import { invalidateSharedIntelligence, sharedIntelligence } from "../shared/resources.js";
import "./strategy-styles.js";

const colors = ["#27c7a8", "#5b9cff", "#8a6ce8", "#e7b65a", "#5fc5e6", "#e26f95"];
const number = input => Number.isFinite(Number(input)) ? Number(input) : 0;
const pct = (input, digits = 1) => `${(number(input) * 100).toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`;
const pp = input => `${number(input) >= 0 ? "+" : ""}${(number(input) * 100).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} p.p.`;
const html = input => String(input ?? "").replace(/[&<>'"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);
const clampPercent = input => Math.max(0, Math.min(100, number(input) * 100));
let strategyDifferencesOpen = false;
const assetLabel = asset => asset.display_label || asset.contract_label || asset.name || asset.ticker;
const assetCurrent = asset => asset.current_weight_in_class ?? asset.class_weight;
const gapText = asset => {
  if (asset.gap_pp === null || asset.gap_pp === undefined) return "Composição atual indisponível";
  if (Math.abs(number(asset.gap_pp)) < .000001) return "Alinhado ao objetivo";
  return `${pct(Math.abs(number(asset.gap_pp)))} ${number(asset.gap_pp) < 0 ? "acima" : "abaixo"} do objetivo`;
};

function composition(classes, field, title, available = true) {
  if (!available) return `<div class="strategy-composition strategy-composition-unavailable"><small>${title}</small><div class="strategy-composition-message">Parte da carteira não pôde ser avaliada.</div></div>`;
  const segments = classes.filter(item => number(item[field]) > 0).map(item => {
    const weight = number(item[field]);
    const context = field === "current_weight" ? "da carteira atual" : "da carteira-alvo";
    const value = field === "current_weight" && item.market_value !== null && item.market_value !== undefined ? ` · ${money(item.market_value)}` : "";
    const description = `${item.label}: ${pct(weight)} ${context}${value}`;
    return `<span title="${html(description)}" aria-label="${html(description)}" style="width:${clampPercent(weight)}%;background:${item.color}">${weight >= .09 ? html(item.label) : ""}</span>`;
  }).join("");
  return `<div class="strategy-composition"><small>${title}</small><div role="img" aria-label="${title}" class="strategy-composition-bar">${segments || "Sem distribuição definida"}</div></div>`;
}

function strategyLegend(classes) {
  return `<div class="strategy-legend" aria-label="Legenda das classes">${classes.filter(item => number(item.current_weight) > 0 || number(item.target_weight) > 0).map(item => `<span><i style="background:${item.color}"></i>${html(item.label)}</span>`).join("")}</div>`;
}

function classGap(item) {
  return number(item.current_weight) - number(item.target_weight);
}

function classGapText(item) {
  const gap = classGap(item);
  if (Math.abs(gap) < .000001) return "No objetivo";
  return `${pct(Math.abs(gap))} ${gap > 0 ? "acima" : "abaixo"} do objetivo`;
}

function strategyDifferences(classes) {
  const relevant = classes.filter(item => number(item.current_weight) > 0 || number(item.target_weight) > 0).sort((left, right) => Math.abs(classGap(right)) - Math.abs(classGap(left)) || left.label.localeCompare(right.label));
  const largest = relevant[0];
  const insight = largest && Math.abs(classGap(largest)) >= .000001 ? `Maior diferença: ${html(largest.label)} · ${html(classGapText(largest))}` : "A distribuição atual está alinhada à carteira-alvo.";
  const rows = relevant.map(item => `<article class="strategy-difference-row"><div class="strategy-difference-heading"><span><i style="background:${item.color}"></i><strong>${html(item.label)}</strong></span><b>${html(classGapText(item))}</b></div><div class="strategy-bullet" role="img" aria-label="${html(item.label)}: atual ${pct(item.current_weight)}, objetivo ${pct(item.target_weight)}, ${html(classGapText(item))}"><i style="width:${clampPercent(item.current_weight)}%;background:${item.color}"></i><b style="left:${clampPercent(item.target_weight)}%"></b></div><div class="strategy-difference-values"><span>Atual <strong>${pct(item.current_weight)}</strong>${item.market_value === null || item.market_value === undefined ? "" : `<small>${money(item.market_value)}</small>`}</span><span>Objetivo <strong>${pct(item.target_weight)}</strong></span><span>Diferença <strong>${pp(classGap(item))}</strong></span></div></article>`).join("");
  return `<details class="strategy-differences" data-strategy-differences${strategyDifferencesOpen ? " open" : ""}><summary aria-expanded="${strategyDifferencesOpen}"><span><small>Onde estão as diferenças?</small><strong>${insight}</strong></span><i aria-hidden="true">⌄</i></summary><div class="strategy-difference-list">${rows}</div></details>`;
}

function zeroTargetContext(classes) {
  const items = classes.filter(item => number(item.current_weight) > 0 && number(item.target_weight) === 0);
  if (!items.length) return "";
  return `<aside class="strategy-context"><p>Contexto da política</p><h2>Sua política não contempla algumas classes que hoje fazem parte da carteira.</h2><div>${items.map(item => `<span>${html(item.label)} <strong>${pct(item.current_weight)}</strong></span>`).join("")}</div><p>Essas classes possuem posição atual, mas não fazem parte da distribuição-alvo cadastrada.</p><strong>Sua carteira se desviou da estratégia ou sua estratégia mudou?</strong><button class="secondary" type="button" data-edit-strategy>Revisar estratégia</button></aside>`;
}

function assetTargets(classes) {
  const configured = classes.filter(item => item.assets.some(asset => asset.target_weight !== null && asset.target_weight !== undefined)).sort((left, right) => number(right.composition_distance) - number(left.composition_distance));
  const unconfigured = classes.filter(item => !item.assets.some(asset => asset.target_weight !== null && asset.target_weight !== undefined));
  const example = `<div class="strategy-asset-example"><p>Exemplo ilustrativo</p><strong>Exterior <span>15% do patrimônio</span></strong><small>Dentro desses 15%:</small><div><span>IVV <b>50%</b></span><span>QQQ <b>30%</b></span><span>IAU <b>20%</b></span></div><em>100% da classe</em></div>`;
  if (!configured.length) return `<section class="strategy-asset-targets"><p>Composição dentro das classes <span>Opcional</span></p><h2>Quer controlar também como cada classe é distribuída?</h2><small>Sua estratégia já define quanto do patrimônio deve ficar em cada classe. Se quiser mais controle, você pode definir objetivos para os ativos dentro de cada uma delas.</small><div>${example}<p class="strategy-asset-helper">Você não precisa definir essa composição. Sem targets individuais, o Income acompanha apenas o objetivo da classe.</p>${classes.some(item => item.assets.length) ? `<button type="button" data-choose-asset-class>Definir composição por ativo</button>` : ""}</div></section>`;
  const ranking = configured.length >= 2 ? `<div class="strategy-distance-ranking"><p>Distância por classe</p>${configured.filter(group => group.composition_distance !== null && group.composition_distance !== undefined).map(group => `<div><span><b>${html(group.label)}</b><strong>${pct(group.composition_distance)}</strong></span><i><b style="width:${number(group.composition_distance) * 100}%"></b></i></div>`).join("")}</div>` : "";
  const cards = configured.map((group, index) => {
    const relevant = group.assets.filter(asset => number(assetCurrent(asset)) > 0 || number(asset.target_weight) > 0).sort((left, right) => Math.abs(number(right.gap_pp)) - Math.abs(number(left.gap_pp)));
    const top = relevant.slice(0, 4).map(asset => `<p class="strategy-gap-row"><span>${html(assetLabel(asset))}</span><strong>${html(gapText(asset).replace(" do objetivo", ""))}</strong></p>`).join("");
    const distance = group.composition_distance === null || group.composition_distance === undefined ? `<div class="strategy-quality"><strong>Composição atual incompleta</strong><small>${html(group.valuation_unavailable_reason || "Parte dos ativos desta classe não possui valuation atual disponível.")}</small></div>` : number(group.composition_distance) === 0 ? `<div class="strategy-aligned">Composição alinhada ao objetivo definido.<strong>Distância ${pct(0)}</strong></div>` : `<div class="strategy-card-distance"><span>Distância da composição</span><strong>${pct(group.composition_distance)}</strong></div>`;
    return `<article class="strategy-insight-card"${index === 0 ? ' data-largest-distance="true"' : ""}><header><div><h3>${html(group.label)}</h3><small>${pct(group.target_weight)} do patrimônio</small></div>${index === 0 && configured.length > 1 ? "<em>Maior distância</em>" : ""}</header>${distance}<div class="strategy-top-gaps"><small>Maiores diferenças</small>${top}${relevant.length > 4 ? `<span>${relevant.length - 4} outros ativos</span>` : ""}</div><footer><button class="secondary" type="button" data-view-composition="${html(group.asset_class)}">Ver composição</button><button class="secondary" type="button" data-edit-asset-target="${html(group.asset_class)}">Editar</button></footer></article>`;
  }).join("");
  const pending = unconfigured.length ? `<div class="strategy-unconfigured"><p>${unconfigured.length} ${unconfigured.length === 1 ? "classe ainda acompanha" : "classes ainda acompanham"} apenas o objetivo da classe.</p>${unconfigured.map(group => `<article><div><strong>${html(group.label)}</strong><small>${pct(group.target_weight)} do patrimônio</small></div><span>Você acompanha apenas o objetivo total da classe.</span>${group.assets.length ? `<button class="secondary" type="button" data-edit-asset-target="${html(group.asset_class)}">Definir composição</button>` : ""}</article>`).join("")}</div>` : "";
  return `<section class="strategy-asset-targets"><p>Composição dentro das classes <span>Opcional</span></p><h2>Como suas classes estão distribuídas por dentro?</h2><small>Veja quais classes estão mais distantes da composição que você definiu e quais ativos concentram as maiores diferenças.</small><div class="strategy-composition-summary"><span>${configured.length} ${configured.length === 1 ? "classe com composição definida" : "classes com composição definida"}</span><span>${unconfigured.length} ${unconfigured.length === 1 ? "acompanhada" : "acompanhadas"} apenas pelo objetivo geral</span></div>${ranking}<div class="strategy-insight-grid">${cards}</div>${pending}</section>`;
}

function render(target, state) {
  const classes = [...state.classes].sort((a, b) => number(b.current_weight) - number(a.current_weight) || a.label.localeCompare(b.label));
  const targetTotal = classes.reduce((total, item) => total + number(item.target_weight), 0);
  const targetValid = Math.abs(targetTotal - 1) < .000001;
  const targetComposition = targetValid ? composition(classes, "target_weight", "Carteira-alvo") : `<div class="strategy-composition strategy-composition-unavailable"><small>Carteira-alvo</small><div class="strategy-composition-message">A distribuição-alvo soma ${pct(targetTotal)}. Revise a estratégia para completar 100%.</div></div>`;
  target.innerHTML = `<section class="strategy-hero"><div class="strategy-hero-heading"><div><p>Minha estratégia</p><h2>Carteira atual × Carteira-alvo</h2></div><button class="secondary" type="button" data-edit-strategy>Editar estratégia</button></div><div class="strategy-compositions">${composition(classes, "current_weight", "Carteira atual", state.valuationComplete !== false)}${targetComposition}</div>${strategyLegend(classes)}<div class="strategy-drift"><div><small>Distância da estratégia</small><strong>${pct(state.analysis.portfolio_drift)}</strong><span>Distância da distribuição-alvo</span></div><p>Representa a diferença agregada entre a distribuição atual e a política cadastrada.</p></div>${strategyDifferences(classes)}</section>${zeroTargetContext(classes)}${assetTargets(classes)}`;
  const details = target.querySelector?.("[data-strategy-differences]");
  details?.addEventListener("toggle", () => { strategyDifferencesOpen = details.open; details.querySelector("summary")?.setAttribute("aria-expanded", String(details.open)); });
  target.querySelectorAll("[data-edit-strategy]").forEach(button => button.addEventListener("click", () => openEditor(state, button)));
  target.querySelectorAll("[data-edit-asset-target]").forEach(button => button.addEventListener("click", () => openAssetEditor(state, button.dataset.editAssetTarget, button)));
  target.querySelectorAll("[data-choose-asset-class]").forEach(button => button.addEventListener("click", () => openAssetClassChooser(state, button)));
  target.querySelectorAll("[data-view-composition]").forEach(button => button.addEventListener("click", () => openCompositionDrawer(state, button.dataset.viewComposition, button)));
}

function compositionDrawer() {
  let node = document.querySelector("#composition-detail-dialog");
  if (node) return node;
  node = document.createElement("dialog"); node.id = "composition-detail-dialog"; node.className = "composition-detail-dialog"; node.innerHTML = `<div data-composition-detail></div>`; node.addEventListener("close", () => node._trigger?.focus()); document.body.append(node); return node;
}

function openCompositionDrawer(state, assetClass, trigger) {
  const group = state.classes.find(item => item.asset_class === assetClass); if (!group) return;
  const node = compositionDrawer(); node._trigger = trigger; const relevant = group.assets.filter(asset => number(assetCurrent(asset)) > 0 || number(asset.target_weight) > 0); let filter = "all"; let order = "gap";
  const draw = () => { const filtered = relevant.filter(asset => filter === "all" || (filter === "above" && number(asset.gap_pp) < 0) || (filter === "below" && number(asset.gap_pp) > 0) || (filter === "aligned" && Math.abs(number(asset.gap_pp)) < .000001)); const sorted = [...filtered].sort((left, right) => order === "current" ? number(assetCurrent(right)) - number(assetCurrent(left)) : order === "target" ? number(right.target_weight) - number(left.target_weight) : order === "name" ? assetLabel(left).localeCompare(assetLabel(right)) : Math.abs(number(right.gap_pp)) - Math.abs(number(left.gap_pp))); const scale = Math.max(.01, ...relevant.flatMap(asset => [number(assetCurrent(asset)), number(asset.target_weight)])) * 1.1; node.querySelector("[data-composition-rows]").innerHTML = sorted.map(asset => `<article class="composition-detail-row"><div><strong>${html(assetLabel(asset))}</strong>${asset.market_value_base === null || asset.market_value_base === undefined ? "" : `<small>${money(asset.market_value_base)}</small>`}</div><div class="composition-bullet" role="img" aria-label="${html(assetLabel(asset))}: atual ${pct(assetCurrent(asset))}, objetivo ${pct(asset.target_weight)}, ${html(gapText(asset))}"><i style="width:${Math.min(100, number(assetCurrent(asset)) / scale * 100)}%"></i><b style="left:${Math.min(100, number(asset.target_weight) / scale * 100)}%"></b></div><p><span>Atual <b>${pct(assetCurrent(asset))}</b></span><span>Objetivo <b>${pct(asset.target_weight)}</b></span><strong>${html(gapText(asset))}</strong></p></article>`).join("") || `<p class="strategy-asset-helper">Nenhum ativo neste filtro.</p>`; };
  node.firstElementChild.innerHTML = `<header><div><p>Composição dentro da classe</p><h2>${html(group.label)}</h2><span>${pct(group.target_weight)} do patrimônio · Distância ${group.composition_distance === null || group.composition_distance === undefined ? "indisponível" : pct(group.composition_distance)}</span><small>Compare a distribuição atual dos ativos desta classe com os objetivos que você definiu.</small></div><button type="button" data-close-composition aria-label="Fechar composição">×</button></header><div class="composition-detail-controls"><div role="group" aria-label="Filtrar ativos"><button data-filter="all" aria-pressed="true">Todos</button><button data-filter="above">Acima</button><button data-filter="below">Abaixo</button><button data-filter="aligned">No objetivo</button></div><label>Ordenar<select data-composition-order><option value="gap">Maior diferença</option><option value="current">Maior peso atual</option><option value="target">Maior objetivo</option><option value="name">Nome</option></select></label></div><div class="composition-detail-rows" data-composition-rows></div>`;
  node.querySelector("[data-close-composition]").addEventListener("click", () => node.close()); node.querySelectorAll("[data-filter]").forEach(button => button.addEventListener("click", () => { filter = button.dataset.filter; node.querySelectorAll("[data-filter]").forEach(item => item.setAttribute("aria-pressed", item === button ? "true" : "false")); draw(); })); node.querySelector("[data-composition-order]").addEventListener("change", event => { order = event.target.value; draw(); }); draw(); node.showModal();
}

function assetClassChooser() {
  let node = document.querySelector("#asset-class-chooser-dialog");
  if (node) return node;
  node = document.createElement("dialog"); node.id = "asset-class-chooser-dialog"; node.className = "strategy-editor-dialog strategy-class-chooser"; node.innerHTML = `<div class="dialog-heading"><div><p>Composição dentro das classes</p><h2>Qual classe você quer distribuir?</h2><p>Escolha uma classe para definir os objetivos dos ativos que já fazem parte dela.</p></div><button class="dialog-close" value="cancel" aria-label="Fechar seleção de classe">×</button></div><div class="strategy-editor-content" data-asset-class-options></div>`; node.querySelector(".dialog-close").addEventListener("click", () => node.close()); node.addEventListener("close", () => node._trigger?.focus()); document.body.append(node); return node;
}

function openAssetClassChooser(state, trigger) {
  const node = assetClassChooser(); node._trigger = trigger; const options = node.querySelector("[data-asset-class-options]");
  options.innerHTML = state.classes.filter(item => item.assets.length).map(item => `<button class="strategy-class-choice" type="button" data-class="${html(item.asset_class)}"><span><strong>${html(item.label)}</strong><small>${pct(item.target_weight)} do patrimônio</small></span><b>${item.assets.length} ${item.assets.length === 1 ? "ativo" : "ativos"}</b><i>›</i></button>`).join("");
  options.querySelectorAll("[data-class]").forEach(button => button.addEventListener("click", () => { node.close(); openAssetEditor(state, button.dataset.class, trigger); })); node.showModal();
}

function assetDialog() {
  let node = document.querySelector("#asset-target-editor-dialog");
  if (node) return node;
  node = document.createElement("dialog"); node.id = "asset-target-editor-dialog"; node.className = "strategy-editor-dialog"; node.innerHTML = `<form method="dialog"><div class="dialog-heading"><div><p>Composição dentro da classe</p><h2 data-asset-editor-title></h2><p data-asset-editor-context>Distribua 100% entre os ativos desta classe.</p></div><button class="dialog-close" value="cancel" aria-label="Fechar editor de composição">×</button></div><div class="strategy-editor-content"><div data-asset-total></div><div data-asset-fields></div><p class="message" data-asset-message role="alert"></p></div><div class="dialog-actions"><button class="secondary" value="cancel">Cancelar</button><button type="submit" data-save-asset-target>Salvar composição</button></div></form>`; node.addEventListener("close", () => node._trigger?.focus()); document.body.append(node); return node;
}

function openAssetEditor(state, assetClass, trigger) {
  const group = state.classes.find(item => item.asset_class === assetClass) || state.classes.find(item => item.assets.length); if (!group) return;
  const node = assetDialog(); node._trigger = trigger; node.querySelector("[data-asset-editor-title]").textContent = group.label; node.querySelector("[data-asset-editor-context]").textContent = `Objetivo da classe: ${pct(group.target_weight)} do patrimônio${group.market_value === null || group.market_value === undefined ? "" : ` · Valor atual: ${money(group.market_value)}`}`; const fields = node.querySelector("[data-asset-fields]"); const total = node.querySelector("[data-asset-total]"); const save = node.querySelector("[data-save-asset-target]"); const message = node.querySelector("[data-asset-message]");
  fields.innerHTML = [...group.assets].sort((left, right) => number(assetCurrent(right)) - number(assetCurrent(left))).map(asset => `<label class="strategy-editor-row"><span><b>${html(assetLabel(asset))}</b><small>Atual ${assetCurrent(asset) === null || assetCurrent(asset) === undefined ? "—" : pct(assetCurrent(asset))} · ${html(gapText(asset))}</small></span><input aria-label="Objetivo para ${html(assetLabel(asset))}" type="number" inputmode="decimal" name="${html(asset.ticker)}" min="0" max="100" step="0.1" value="${(number(asset.target_weight) * 100).toFixed(1)}"><b>%</b></label>`).join("");
  const refresh = () => { const values = [...fields.querySelectorAll("input")].map(input => Number(input.value)); const valid = values.every(item => Number.isFinite(item) && item >= 0 && item <= 100); const sum = values.reduce((total, item) => total + (Number.isFinite(item) ? item : 0), 0); const remaining = 100 - sum; total.innerHTML = `<strong>${sum.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}% da classe${valid && Math.abs(remaining) < .000001 ? " ✓" : ""}</strong><span>${!valid ? "Informe valores entre 0% e 100%." : Math.abs(remaining) < .000001 ? "A composição da classe está completa." : remaining > 0 ? `Faltam ${remaining.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}% para completar a classe.` : `Reduza ${Math.abs(remaining).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%.`}</span>`; save.disabled = !valid || Math.abs(remaining) >= .000001; };
  fields.addEventListener("input", refresh); node.querySelector("form").onsubmit = async event => { if (!event.submitter.matches("[data-save-asset-target]")) return; event.preventDefault(); const targets = Object.fromEntries([...fields.querySelectorAll("input")].map(input => [input.name, Number(input.value) / 100])); try { save.disabled = true; save.textContent = "Salvando…"; await portfolioApi.assetAllocationPolicy({ [group.asset_class]: targets }); invalidateSharedIntelligence(); node.close(); await loadStrategy(); } catch (error) { message.textContent = friendlyError(error); save.textContent = "Salvar composição"; refresh(); } }; refresh(); node.showModal();
}

function dialog() {
  let node = document.querySelector("#strategy-editor-dialog");
  if (node) return node;
  node = document.createElement("dialog"); node.id = "strategy-editor-dialog"; node.className = "strategy-editor-dialog"; node.innerHTML = `<form method="dialog"><div class="dialog-heading"><div><p>Minha estratégia</p><h2>Editar estratégia</h2><p>Distribua 100% entre as classes que fazem parte do seu plano.</p></div><button class="dialog-close" value="cancel" aria-label="Fechar editor de estratégia">×</button></div><div class="strategy-editor-content"><div data-strategy-total></div><div data-strategy-fields></div><p class="message" data-strategy-message role="alert"></p></div><div class="dialog-actions"><button class="secondary" value="cancel">Cancelar</button><button type="submit" data-save-strategy>Salvar estratégia</button></div></form>`; node.addEventListener("close", () => node._trigger?.focus()); document.body.append(node); return node;
}

function openEditor(state, trigger) {
  const node = dialog(); node._trigger = trigger; const fields = node.querySelector("[data-strategy-fields]"); const total = node.querySelector("[data-strategy-total]"); const save = node.querySelector("[data-save-strategy]"); const message = node.querySelector("[data-strategy-message]");
  fields.innerHTML = state.classes.map(item => `<label class="strategy-editor-row"><span><b>${html(item.label)}</b>${number(item.current_weight) > 0 && number(item.target_weight) === 0 ? `<small>Atual ${pct(item.current_weight)} · Você possui posição nesta classe.</small>` : ""}</span><input aria-label="Objetivo para ${html(item.label)}" type="number" inputmode="decimal" name="${html(item.asset_class)}" min="0" max="100" step="0.1" value="${(number(item.target_weight) * 100).toFixed(1)}"><b>%</b></label>`).join("");
  const refresh = () => { const values = [...fields.querySelectorAll("input")].map(input => Number(input.value)); const valid = values.every(item => Number.isFinite(item) && item >= 0 && item <= 100); const sum = values.reduce((total, item) => total + (Number.isFinite(item) ? item : 0), 0); const remaining = 100 - sum; total.innerHTML = `<strong>${sum.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}% definidos${valid && Math.abs(remaining) < .000001 ? " ✓" : ""}</strong><span>${!valid ? "Informe valores entre 0% e 100%." : Math.abs(remaining) < .000001 ? "Sua distribuição está completa." : remaining > 0 ? `Faltam ${remaining.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}% para completar sua estratégia.` : `Reduza ${Math.abs(remaining).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%.`}</span>`; save.disabled = !valid || Math.abs(remaining) >= .000001; };
  fields.addEventListener("input", refresh); node.querySelector("form").onsubmit = async event => { if (!event.submitter.matches("[data-save-strategy]")) return; event.preventDefault(); const targets = Object.fromEntries([...fields.querySelectorAll("input")].map(input => [input.name, Number(input.value) / 100])); try { save.disabled = true; save.textContent = "Salvando…"; await portfolioApi.allocationPolicy(targets); invalidateSharedIntelligence(); node.close(); await loadStrategy(); } catch (error) { message.textContent = friendlyError(error); save.textContent = "Salvar estratégia"; refresh(); } }; refresh(); node.showModal();
}

function noPolicy(target, holdings) { const classes = holdings.classes || []; target.innerHTML = `<section class="strategy-empty"><p>Minha estratégia</p><h2>Defina como você quer distribuir seu patrimônio.</h2><p>Uma estratégia permite comparar sua carteira atual com a distribuição que você deseja manter.</p><button type="button" data-create-strategy>Criar estratégia</button></section>`; target.querySelector("[data-create-strategy]").addEventListener("click", event => openEditor({ classes: classes.map(group => ({ ...group, current_weight: group.weight || 0, target_weight: 0 })) }, event.currentTarget)); }

export async function loadStrategy() {
  const target = document.querySelector("#strategy-workspace"); if (!target) return; target.innerHTML = `<div class="strategy-skeleton" aria-busy="true"><span></span><span></span></div>`;
  try { const [holdings, intelligence] = await Promise.all([portfolioApi.holdings(), sharedIntelligence()]); const drift = intelligence.findings?.find(finding => finding.code === "PORTFOLIO_DRIFT"); try { const analysis = drift ? { portfolio_drift: drift.current_value, comparisons: drift.decomposition.map(item => ({ asset_class: item.asset_class, current_weight: item.current_weight, target_weight: item.target_weight, deviation: Number(item.deviation_pp) / 100 })) } : await portfolioApi.allocationAnalysis(); const groups = new Map(holdings.classes.map(group => [group.asset_class, group])); const classes = analysis.comparisons.map((comparison, index) => ({ ...comparison, ...(groups.get(comparison.asset_class) || {}), label: groups.get(comparison.asset_class)?.label || assetClassLabel(comparison.asset_class), market_value: groups.get(comparison.asset_class)?.market_value ?? null, assets: groups.get(comparison.asset_class)?.assets || [], color: colors[index % colors.length] })); render(target, { analysis, classes, valuationComplete: holdings.valuation_complete }); } catch (error) { if (String(error.message || error).includes("política")) noPolicy(target, holdings); else throw error; } } catch { target.innerHTML = `<div class="strategy-error" role="alert"><p>Não foi possível carregar sua estratégia agora.</p><button class="secondary" type="button" data-retry-strategy>Tentar novamente</button></div>`; target.querySelector("[data-retry-strategy]").addEventListener("click", loadStrategy); }
}
export function bindStrategy() { loadStrategy(); }
