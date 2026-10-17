import "./attention-center-styles.js";
import { invalidateSharedIntelligence, sharedIntelligence } from "../shared/resources.js";

const html = value => String(value ?? "").replace(/[&<>'"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);
const percent = value => `${(Number(value || 0) * 100).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
const materiality = { HIGH: 0, MEDIUM: 1, LOW: 2 };
const trajectory = { NEW: 0, WORSENING: 1, PERSISTENT: 2, IMPROVING: 3, UNKNOWN: 4 };
const trajectoryLabel = { NEW: "Novo", WORSENING: "Piorando", IMPROVING: "Melhorando", PERSISTENT: "Persistente" };

function findingView(finding) {
  if (finding.code === "PORTFOLIO_DRIFT") return { category: "Estratégia", title: "Sua carteira está distante da política definida.", metric: percent(finding.current_value), label: "Distância da distribuição-alvo", action: "Ver estratégia", destination: "estrategia" };
  if (finding.code === "COUNTRY_CONCENTRATION") { const difference = (Number(finding.current_value) - Number(finding.reference?.value || 0)) * 100; return { category: "Exposição", title: `Grande parte da carteira está associada ao ${finding.subject?.label || "Brasil"}.`, metric: percent(finding.current_value), label: `Referência do Income: ${percent(finding.reference?.value)}`, comparison: `${difference.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} p.p. acima da referência`, action: "Explorar exposição", destination: "risco-exposicao" }; }
  if (finding.code === "INCOMPLETE_RISK_COVERAGE") return { category: "Limitação", title: "Cobertura de dados de risco ainda é parcial", metric: percent(finding.current_value), label: "do patrimônio investido possui série de preços disponível", comparison: "Isso não significa que esse percentual do risco esteja mensurado.", action: "Ver detalhes", destination: "risco-exposicao" };
  return { category: "Observação", title: finding.title || "Observação patrimonial", metric: percent(finding.current_value), label: "Situação atual", action: "Ver contexto", destination: finding.category === "STRATEGY" ? "estrategia" : "entender" };
}

function card(finding, quality = false) {
  const view = findingView(finding); const trend = trajectoryLabel[finding.trajectory];
  return `<article class="attention-center-card${quality ? " attention-center-card--quality" : ""}"><div class="attention-center-meta"><span>${html(view.category)}</span>${trend ? `<em>${html(trend)}</em>` : ""}</div><h3>${html(view.title)}</h3><strong>${html(view.metric)}</strong><p>${html(view.label)}</p>${view.comparison ? `<small>${html(view.comparison)}</small>` : ""}<a href="#${html(view.destination)}" data-attention-destination data-navigate>${html(view.action)}</a></article>`;
}

function drawer() {
  let node = document.querySelector("#attention-center-drawer"); if (node) return node;
  node = document.createElement("dialog"); node.id = "attention-center-drawer"; node.className = "attention-center-drawer"; node.innerHTML = `<div data-attention-center-content></div>`; node.addEventListener("close", () => node._trigger?.focus()); document.body.append(node); return node;
}

function renderDrawer(state) {
  const node = drawer(); const content = node.querySelector("[data-attention-center-content]");
  if (state.error) { content.innerHTML = `<header><h2>Pontos de atenção</h2><button data-close-attention aria-label="Fechar">×</button></header><div class="attention-center-state" role="alert"><p>Não foi possível atualizar os pontos de atenção.</p><button data-retry-attention>Tentar novamente</button></div>`; }
  else { const patrimonial = state.patrimonial; const quality = state.quality; const summary = patrimonial.length ? `${patrimonial.length} ${patrimonial.length === 1 ? "ponto merece" : "pontos merecem"} sua atenção` : quality.length ? "Nenhum ponto patrimonial relevante identificado." : "Nenhum ponto relevante identificado com os dados disponíveis."; content.innerHTML = `<header><div><h2>Pontos de atenção</h2><p>${html(summary)}</p>${quality.length ? `<small>${quality.length} ${quality.length === 1 ? "limitação afeta" : "limitações afetam"} algumas análises</small>` : ""}</div><button data-close-attention aria-label="Fechar pontos de atenção">×</button></header>${patrimonial.length ? `<section><h3>Merece atenção</h3>${patrimonial.map(item => card(item)).join("")}</section>` : ""}${quality.length ? `<section class="attention-center-quality"><h3>Limitações da análise</h3>${quality.map(item => card(item, true)).join("")}</section>` : ""}${!patrimonial.length && !quality.length ? `<div class="attention-center-state"><p>${html(summary)}</p></div>` : ""}`; }
  content.querySelector("[data-close-attention]")?.addEventListener("click", () => node.close()); content.querySelector("[data-retry-attention]")?.addEventListener("click", () => { invalidateSharedIntelligence(); loadAttentionCenter(); }); content.querySelectorAll("[data-attention-destination]").forEach(link => link.addEventListener("click", () => node.close()));
}

const state = { patrimonial: [], quality: [], error: false, loaded: false };
let attentionBound = false;
export function attentionGroups(payload) { const surfaced = (payload.findings || []).filter(item => item.should_surface); return { patrimonial: surfaced.filter(item => item.category !== "DATA_QUALITY").sort((a, b) => (materiality[a.materiality] ?? 9) - (materiality[b.materiality] ?? 9) || (trajectory[a.trajectory] ?? 9) - (trajectory[b.trajectory] ?? 9) || String(a.logical_key).localeCompare(String(b.logical_key))), quality: surfaced.filter(item => item.category === "DATA_QUALITY") }; }
function updateControl() { const button = document.querySelector("#attention-center-trigger"); if (!button) return; const patrimonialCount = state.patrimonial.length; const qualityCount = state.quality.length; const count = patrimonialCount + qualityCount; const parts = []; if (patrimonialCount) parts.push(`${patrimonialCount} ${patrimonialCount === 1 ? "ponto patrimonial" : "pontos patrimoniais"}`); if (qualityCount) parts.push(`${qualityCount} ${qualityCount === 1 ? "limitação de análise" : "limitações de análise"}`); const label = state.error ? "Não foi possível atualizar os pontos de atenção" : count ? parts.join(" e ") : "Pontos de atenção — nenhum ponto relevante identificado"; button.setAttribute("aria-label", label); button.title = label; button.dataset.state = state.error ? "error" : patrimonialCount ? "attention" : qualityCount ? "quality" : "neutral"; button.querySelector("[data-attention-badge]").textContent = count ? (count >= 10 ? "9+" : String(count)) : ""; button.querySelector("[data-attention-badge]").hidden = !count; }
export async function loadAttentionCenter() { try { const groups = attentionGroups(await sharedIntelligence()); state.patrimonial = groups.patrimonial; state.quality = groups.quality; state.error = false; state.loaded = true; } catch { state.error = true; state.loaded = true; } updateControl(); if (drawer().open) renderDrawer(state); }
export function bindAttentionCenter() { if (attentionBound) return; const button = document.querySelector("#attention-center-trigger"); if (!button) return; attentionBound = true; button.addEventListener("click", () => { const node = drawer(); node._trigger = button; renderDrawer(state); node.showModal(); }); const legacy = window.location.hash === "#pontos-atencao"; if (legacy) { window.location.hash = "minha-carteira"; queueMicrotask(() => button.click()); } document.addEventListener("portfolio:intelligence-refresh", () => { invalidateSharedIntelligence(); loadAttentionCenter(); }); }
