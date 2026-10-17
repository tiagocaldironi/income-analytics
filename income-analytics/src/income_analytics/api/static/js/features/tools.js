import { portfolioApi } from "../api.js";
import { percentage } from "../shared/ui.js";

const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, character => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[character]));
let toolsSetup = false;
const rankingState = { page: 1, pageSize: 25, query: "", excludeRetail: false, excludeAviation: false };
let searchTimer;
let currentSnapshotId;

const unavailable = value => value === null || value === undefined || value === ""
  ? "Não disponível" : escapeHtml(value);
const formatMoney = value => {
  if (value === null || value === undefined || value === "") return "Não disponível";
  const amount = Number(value);
  if (!Number.isFinite(amount)) return "Não disponível";
  const compact = Math.abs(amount) >= 1e9 ? amount / 1e9
    : Math.abs(amount) >= 1e6 ? amount / 1e6 : amount;
  const suffix = Math.abs(amount) >= 1e9 ? " bi" : Math.abs(amount) >= 1e6 ? " mi" : "";
  return `R$ ${new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 0, maximumFractionDigits: suffix ? 1 : 2,
  }).format(compact)}${suffix}`;
};
const formatDate = value => {
  if (!value) return "Não disponível";
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return match ? `${match[3]}/${match[2]}/${match[1]}` : escapeHtml(value);
};
const ratioPercentage = value => percentage(Number(value) * 100);

export function setupToolsRoutes() {
  if (toolsSetup) return;
  toolsSetup = true;
  const nav = document.querySelector(".primary-nav");
  const settingsLink = nav?.querySelector('a[href="#configuracoes"]');
  if (settingsLink) settingsLink.insertAdjacentHTML("beforebegin", '<a href="#ferramentas" data-navigate title="Ferramentas">Ferramentas</a>');
  else nav?.insertAdjacentHTML("beforeend", '<a href="#ferramentas" data-navigate title="Ferramentas">Ferramentas</a>');
  document.querySelector("main")?.insertAdjacentHTML("beforeend", '<section class="page" data-page="ferramentas" hidden><div class="page-intro"><p class="eyebrow">Oportunidades</p><h1>Encontre oportunidades</h1><p>Ferramentas quantitativas para analisar e comparar investimentos.</p></div><section class="grid-two" id="tools-list">Carregando ferramentas…</section><p class="field-help">Os rankings são ferramentas quantitativas de análise e não constituem recomendação de investimento.</p></section>');
  document.querySelector("main")?.insertAdjacentHTML("beforeend", '<section class="page" data-page="tools-magic-formula-stocks" hidden><div class="page-intro"><p class="eyebrow">Fórmula Mágica · MF_BR_2027_V1</p><h1>Fórmula Mágica</h1><p id="stock-tool-status">Carregando ranking…</p><a href="#ferramentas" data-navigate>Voltar para Ferramentas</a></div><section id="magic-formula-ranking" class="card"><div class="mf-loading" role="status">Carregando ranking…</div></section></section><section class="page" data-page="tools-magic-formula-fiis" hidden><div class="page-intro"><p class="eyebrow">MF-FII v3</p><h1>Ranking por segmento</h1><p id="fii-tool-status">Carregando estado dos dados…</p><a href="#ferramentas" data-navigate>Voltar para Ferramentas</a></div></section>');
  bindRankingControls();
}

export async function loadTools() {
  setupToolsRoutes();
  const target = document.querySelector("#tools-list");
  target.innerHTML = "Carregando ferramentas…";
  try {
    const data = await portfolioApi.tools();
    target.innerHTML = data.items.map(tool => `<article class="card"><h2>${tool.icon} ${tool.name}</h2><p>${tool.description}</p><p><strong>${tool.status === "DATA_GAP" ? "Dados em preparação" : tool.status}</strong> · ${tool.version}</p><a class="button-link" href="#${tool.route}" data-navigate>Explorar</a><p class="field-help">Metodologia e critérios de elegibilidade serão exibidos nesta ferramenta.</p></article>`).join("");
  } catch {
    target.innerHTML = 'Não foi possível carregar as ferramentas. <button type="button" data-tools-retry>Recarregar</button>';
    target.querySelector("[data-tools-retry]")?.addEventListener("click", loadTools, { once: true });
    const ranking = document.querySelector("#magic-formula-ranking");
    if (ranking) renderRankingError(ranking);
  }
}

export async function loadMagicFormulaStocksRoute() {
  setupToolsRoutes();
  await loadRanking();
}

export async function loadMagicFormulaFiisRoute() {
  setupToolsRoutes();
  const target = document.querySelector("#fii-tool-status");
  try {
    const fiis = await portfolioApi.magicFormulaFiis();
    target.textContent = `${fiis.data_status}: ${fiis.message}`;
  } catch {
    target.textContent = "Não foi possível carregar o ranking de FIIs.";
  }
}

export async function bindTools() {
  setupToolsRoutes();
  return loadTools();
}

function bindRankingControls() {
  const target = document.querySelector("#magic-formula-ranking");
  if (!target || target.dataset.bound) return;
  target.dataset.bound = "true";
  const updateSearch = event => {
    if (!event.target.matches("[name=mf-search]")) return;
    rankingState.query = event.target.value;
    rankingState.page = 1;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadRanking, event.type === "change" ? 0 : 250);
  };
  target.addEventListener("input", updateSearch);
  target.addEventListener("keyup", updateSearch);
  target.addEventListener("change", updateSearch);
  target.addEventListener("change", event => {
    if (event.target.matches("[name=mf-retail]")) rankingState.excludeRetail = event.target.checked;
    if (event.target.matches("[name=mf-aviation]")) rankingState.excludeAviation = event.target.checked;
    if (event.target.matches("[name=mf-retail], [name=mf-aviation]")) {
      rankingState.page = 1;
      loadRanking();
    }
  });
  target.addEventListener("click", event => {
    if (event.target.closest("[data-mf-retry]")) {
      loadRanking();
      return;
    }
    const button = event.target.closest("[data-mf-page]");
    if (button) {
      rankingState.page = Number(button.dataset.mfPage);
      loadRanking();
      return;
    }
    const companyButton = event.target.closest("[data-mf-detail]");
    if (companyButton) {
      const item = JSON.parse(companyButton.dataset.mfDetail);
      openCompanyDetail(item, currentSnapshotId, companyButton);
    }
    if (event.target.closest("[data-mf-detail-retry]")) {
      const retry = event.target.closest("[data-mf-detail-retry]");
      openCompanyDetail(
        JSON.parse(retry.dataset.mfDetailRetry),
        retry.dataset.snapshotId,
        document.querySelector("#mf-company-detail")?._mfOpener,
      );
    }
  });
}

async function loadRanking() {
  const target = document.querySelector("#magic-formula-ranking");
  if (!target) return;
  target.setAttribute("aria-busy", "true");
  try {
    renderMagicFormulaRanking(await portfolioApi.magicFormulaStocks(rankingState));
  } catch {
    renderRankingError(target);
  } finally {
    target.removeAttribute("aria-busy");
  }
}

function renderMagicFormulaRanking(data) {
  const target = document.querySelector("#magic-formula-ranking");
  if (!target) return;
  if (data.status === "NO_PUBLISHED_RANKING" || !data.snapshot_available) {
    document.querySelector("#stock-tool-status").textContent = "Ranking ainda não disponível.";
    target.innerHTML = '<p role="status">O ranking ainda não está disponível.</p><button type="button" data-mf-retry>Tentar novamente</button>';
    return;
  }
  if (!data.snapshot || !Array.isArray(data.items) || !data.summary || !Number.isInteger(data.total)) {
    throw new Error("INVALID_MAGIC_FORMULA_RESPONSE");
  }
  const summary = data.summary;
  currentSnapshotId = data.snapshot.ranking_snapshot_id;
  const detailButton = item => `<button type="button" class="mf-detail" aria-label="Ver empresa ${escapeHtml(item.selected_security)}" data-mf-detail="${escapeHtml(JSON.stringify(item))}">Ver empresa</button>`;
  const sectorCell = item => `<span class="mf-sector" title="${escapeHtml(item.sector || "Setor não disponível")}">${unavailable(item.sector)}</span>`;
  const rows = data.items.map(item => `<tr><td>${item.global_rank}</td><td><strong>${escapeHtml(item.selected_security)}</strong><small>${escapeHtml(item.company_name)}</small></td><td>${sectorCell(item)}</td><td>${ratioPercentage(item.earnings_yield)}</td><td>${item.earnings_yield_rank}</td><td>${ratioPercentage(item.return_on_capital)}</td><td>${item.return_on_capital_rank}</td><td>${item.combined_score}</td><td>${detailButton(item)}</td></tr>`).join("");
  const mobileRows = data.items.map(item => `<article class="mf-mobile-card"><h3>#${item.global_rank} · ${escapeHtml(item.selected_security)}</h3><p>${escapeHtml(item.company_name)}</p><dl><dt>Setor</dt><dd>${sectorCell(item)}</dd><dt>EY</dt><dd>${ratioPercentage(item.earnings_yield)}</dd><dt>ROC</dt><dd>${ratioPercentage(item.return_on_capital)}</dd><dt>Pontuação</dt><dd>${item.combined_score}</dd></dl>${detailButton(item)}</article>`).join("");
  const pages = data.pages || 1;
  const rankingDate = data.snapshot.ranking_as_of_date || data.snapshot.ranking_reference_date;
  const financialCutoff = data.snapshot.financial_information_cutoff || data.snapshot.accounting_cutoff;
  document.querySelector("#stock-tool-status").textContent = `Ranking em: ${rankingDate} · dados financeiros: informações públicas disponíveis até ${financialCutoff}`;
  target.innerHTML = `<div class="mf-summary" aria-label="Cobertura do universo"><article><strong>${summary.ranked}</strong><span>ranqueadas</span></article><article><strong>${summary.blocked}</strong><span>bloqueadas por dados</span></article><article><strong>${summary.reviews}</strong><span>em review</span></article><article><strong>${summary.liquidity_fail}</strong><span>liquidez insuficiente</span></article><article><strong>${summary.methodological_coverage}</strong><span>cobertura metodológica</span></article><article><strong>${summary.conservative_coverage}</strong><span>cobertura conservadora</span></article></div><div class="mf-toolbar"><label>Buscar empresa ou ticker<input name="mf-search" type="search" value="${escapeHtml(rankingState.query)}" placeholder="Ex.: WEGE3"></label><label><input name="mf-retail" type="checkbox" ${rankingState.excludeRetail ? "checked" : ""}> Ocultar varejo tradicional</label><label><input name="mf-aviation" type="checkbox" ${rankingState.excludeAviation ? "checked" : ""}> Ocultar aviação</label></div><p>${data.total} empresas nesta visualização · ranking global preservado após filtros.</p>${data.items.length ? `<div class="table-wrap mf-table-wrap"><table><thead><tr><th>Posição</th><th>Empresa</th><th>Setor</th><th><span tabindex="0" aria-label="Sobre Earnings Yield" title="Earnings Yield relaciona EBIT ao Enterprise Value. Valores maiores recebem posições melhores.">EY ⓘ</span></th><th>Rank EY</th><th><span tabindex="0" aria-label="Sobre Retorno sobre Capital" title="Retorno sobre Capital relaciona EBIT ao capital empregado da metodologia. Valores maiores recebem posições melhores.">ROC ⓘ</span></th><th>Rank ROC</th><th><span tabindex="0" aria-label="Sobre pontuação combinada" title="Combined Score = rank EY + rank ROC. Quanto menor, melhor a posição combinada.">Pontuação ⓘ</span></th><th>Ações</th></tr></thead><tbody>${rows}</tbody></table></div><div class="mf-mobile-cards">${mobileRows}</div>` : '<p>Nenhuma empresa encontrada com os filtros atuais.</p>'}<nav class="mf-pagination" aria-label="Paginação"><button type="button" data-mf-page="${Math.max(1, data.page - 1)}" ${data.page <= 1 ? "disabled" : ""}>Anterior</button><span>Página ${data.page} de ${pages}</span><button type="button" data-mf-page="${Math.min(pages, data.page + 1)}" ${data.page >= pages ? "disabled" : ""}>Próxima</button></nav><details class="mf-methodology"><summary>Como funciona?</summary><p>A Fórmula Mágica combina dois indicadores: Earnings Yield, que relaciona o EBIT ao Enterprise Value, e Retorno sobre Capital, que relaciona o EBIT ao capital empregado conforme a metodologia. Os ranks são somados; quanto menor o score, melhor a posição combinada. A classificação exibida não constitui recomendação de investimento.</p><p>Varejo e aviação não são excluídos da metodologia. Esses setores podem ser ocultados usando os filtros da tela; os filtros preservam a posição global.</p><p>O setor econômico é metadado descritivo da CVM, separado dos dados point-in-time do ranking. A taxonomia disponível não inclui subsetor ou segmento econômico estruturado.</p></details><p class="field-help">${summary.metric_non_rankable} empresas com dados completos não receberam posição porque EV ou capital empregado não é positivo; os dados permanecem visíveis no estado do universo.</p>`;
}

async function openCompanyDetail(item, snapshotId, opener) {
  let detail = document.querySelector("#mf-company-detail");
  if (!detail) {
    detail = document.createElement("dialog");
    detail.id = "mf-company-detail";
    detail.className = "mf-company-drawer";
    document.body.append(detail);
    detail.addEventListener("close", () => {
      detail.removeAttribute("aria-busy");
      detail.dataset.companyId = "";
      detail._mfOpener?.focus();
      detail._mfOpener = null;
    });
  }
  detail._mfOpener = opener;
  detail.dataset.companyId = item.company_id;
  detail.dataset.snapshotId = snapshotId || "";
  if (!detail.open) detail.showModal();
  detail.setAttribute("aria-busy", "true");
  detail.innerHTML = `<button type="button" class="mf-dialog-close" aria-label="Fechar detalhes" data-mf-close>×</button><p class="mf-drawer-eyebrow">${escapeHtml(item.selected_security)} · ranking #${item.global_rank}</p><h2 id="mf-detail-title">Detalhes da empresa</h2><div class="mf-skeleton" role="status" aria-label="Carregando detalhes"><span></span><span></span><span></span><span></span></div>`;
  detail.setAttribute("aria-labelledby", "mf-detail-title");
  detail.querySelector("[data-mf-close]").addEventListener("click", () => detail.close());
  try {
    const result = await portfolioApi.magicFormulaStockDetail(item.company_id, snapshotId);
    if (!detail.isConnected || detail.dataset.companyId !== item.company_id) return;
    renderCompanyDetail(detail, result);
  } catch {
    detail.innerHTML = `<button type="button" class="mf-dialog-close" aria-label="Fechar detalhes" data-mf-close>×</button><h2 id="mf-detail-title">Detalhes da empresa</h2><p role="alert">Não foi possível carregar os detalhes desta empresa.</p><button type="button" data-mf-detail-retry="${escapeHtml(JSON.stringify(item))}" data-snapshot-id="${escapeHtml(snapshotId || "")}">Tentar novamente</button>`;
    detail.querySelector("[data-mf-close]").addEventListener("click", () => detail.close());
  } finally {
    detail.removeAttribute("aria-busy");
  }
  if (!opener?.isConnected) detail.querySelector("[data-mf-close]")?.focus();
}

function renderCompanyDetail(detail, response) {
  const { company, ranking, calculation, data_basis: basis, provenance } = response;
  if (!company || !ranking || !calculation || !basis) throw new Error("INVALID_COMPANY_DETAIL");
  const exact = value => value === null || value === undefined ? "Não disponível" : escapeHtml(value);
  const exactMoney = key => {
    const value = calculation[key];
    return value === null || value === undefined ? "Não disponível"
      : `<span title="Valor exato: R$ ${escapeHtml(value)}">${formatMoney(value)}</span>`;
  };
  const accounting = Array.isArray(provenance.accounting) ? provenance.accounting : [];
  const sources = accounting.map(source => `<li>${escapeHtml(source.metric)} · ${escapeHtml(source.statement)} ${escapeHtml(source.account_code)}<small>${escapeHtml(source.source_reference)}</small></li>`).join("");
  const sector = unavailable(company.sector);
  const why = `A Fórmula Mágica combina a posição em Earnings Yield (#${ranking.earnings_yield_rank}) com a posição em Retorno sobre Capital (#${ranking.return_on_capital_rank}). A soma resulta no score ${ranking.combined_score} e na posição global #${ranking.global_rank}.`;
  detail.innerHTML = `<button type="button" class="mf-dialog-close" aria-label="Fechar detalhes" data-mf-close>×</button><p class="mf-drawer-eyebrow">Detalhes da empresa</p><h2 id="mf-detail-title">${escapeHtml(company.ticker)} · ${escapeHtml(company.company_name)}</h2><p class="mf-global-rank">#${ranking.global_rank} <span>no ranking global em ${formatDate(response.snapshot.ranking_as_of_date)}</span></p><section class="mf-detail-section"><h3>Setor</h3><p>${sector}</p><small>Classificação CVM usada como metadado descritivo atual. Data de disponibilidade histórica: não conhecida; não compõe nem justifica o ranking point-in-time.</small></section><section class="mf-detail-section"><h3>Fórmula Mágica</h3><div class="mf-detail-metrics"><article><span tabindex="0" aria-label="Definição de Earnings Yield" title="Earnings Yield = EBIT / Enterprise Value. Valores maiores recebem posições melhores.">Earnings Yield ⓘ</span><strong>${ratioPercentage(ranking.earnings_yield)}</strong><small>Rank #${ranking.earnings_yield_rank}</small></article><article><span tabindex="0" aria-label="Definição de Retorno sobre Capital" title="Retorno sobre Capital relaciona EBIT ao capital empregado conforme a metodologia.">Retorno sobre Capital ⓘ</span><strong>${ratioPercentage(ranking.return_on_capital)}</strong><small>Rank #${ranking.return_on_capital_rank}</small></article><article><span tabindex="0" aria-label="Definição de pontuação combinada" title="Combined Score = rank EY + rank ROC. Quanto menor, melhor a posição combinada.">Pontuação ⓘ</span><strong>${ranking.combined_score}</strong></article><article><span>Posição global</span><strong>#${ranking.global_rank}</strong></article></div><h4>Por que está nesta posição?</h4><p>${why}</p></section><section class="mf-detail-section"><h3>Dados utilizados no cálculo</h3><dl><dt>EBIT</dt><dd>${exactMoney("ebit")}</dd><dt>Enterprise Value</dt><dd>${exactMoney("enterprise_value")}</dd><dt>Capital empregado</dt><dd>${exactMoney("capital_employed")}</dd><dt>Preço da ação utilizado</dt><dd>${exactMoney("share_price")}</dd><dt>Valor de mercado</dt><dd>${exactMoney("market_cap")}</dd><dt>Caixa</dt><dd>${exactMoney("cash")}</dd><dt>Dívida</dt><dd>${exactMoney("debt")}</dd><dt>Ações em circulação</dt><dd>${exact(calculation.shares_outstanding)}</dd></dl><p class="mf-note">Valores ausentes no contrato do snapshot aparecem como “Não disponível”; nenhum dado atual é usado como substituto.</p></section><section class="mf-detail-section"><h3>Base dos dados</h3><dl><dt>Documento financeiro</dt><dd>${exact(basis.financial_document_type)}</dd><dt>Período contábil</dt><dd>${formatDate(basis.financial_reference_period)}</dd><dt>Publicado/recebido em</dt><dd>${formatDate(basis.filing_date)}</dd><dt>Cotação</dt><dd>${formatDate(basis.price_date)}</dd><dt>Fonte financeira</dt><dd>${exact(basis.financial_source)}</dd><dt>Fonte do preço</dt><dd>${exact(basis.price_source)}</dd></dl><p class="mf-point-in-time">O ranking utiliza apenas informações que já estavam publicamente disponíveis na data de referência.</p><small>O setor é metadado descritivo; sua disponibilidade histórica é desconhecida.</small></section><details class="mf-detail-section mf-technical"><summary>Informações técnicas e proveniência</summary><dl><dt>Código CVM</dt><dd>${exact(company.cvm_code)}</dd><dt>ISIN</dt><dd>${exact(company.isin)}</dd><dt>Snapshot</dt><dd>${escapeHtml(response.snapshot.ranking_snapshot_id)}</dd><dt>Hash do ranking</dt><dd>${escapeHtml(response.snapshot.ranking_hash)}</dd><dt>Fonte do setor</dt><dd>${exact(company.sector_source_reference)}</dd></dl><h4>Fontes contábeis</h4><ul>${sources || "<li>Não disponível</li>"}</ul><h4>Fontes de mercado</h4><ul><li>Preço: ${exact(provenance.selected_security_source?.price_source_reference)}</li><li>Capital: ${exact(provenance.market?.capital_source_reference)}</li><li>Identidade do papel: ${exact(provenance.selected_security_source?.source_reference)}</li></ul></details>`;
  detail.querySelector("[data-mf-close]").addEventListener("click", () => detail.close());
  detail.setAttribute("aria-labelledby", "mf-detail-title");
  detail.querySelector("[data-mf-close]").focus();
}

function renderRankingError(target) {
  target.innerHTML = '<p role="alert">Não foi possível carregar o ranking.</p><button type="button" data-mf-retry>Tentar novamente</button>';
}
