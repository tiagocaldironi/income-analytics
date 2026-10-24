import { portfolioApi } from "../api.js";
let generation = 0;
export function portfolioIsEmpty(data) {
  const hasAssets = data.holdings.classes.some(group => group.assets.some(asset => !asset.target_only));
  const boundary = data.history?.history_boundary || data.portfolio.history_boundary;
  // The read model may emit a zero baseline snapshot even without any events.
  const hasHistory = boundary?.source === "NO_OBSERVED_FINANCIAL_EVENTS" ? false : Boolean(data.history?.snapshots?.length);
  return !hasAssets && !hasHistory &&
    ![data.portfolio.total_market_value,data.portfolio.total_contributions,data.portfolio.income_received,data.portfolio.cash].some(value => Number(value || 0) !== 0);
}
export async function renderPortfolioGuidance(data) {
  const target = document.querySelector("#portfolio-guidance");
  if (!target) return;
  const sequence = ++generation;
  const id = localStorage.getItem("income.activePortfolioId");
  const empty = portfolioIsEmpty(data);
  const page = document.querySelector('[data-page="minha-carteira"]');
  page.dataset.empty = String(empty);
  if (empty) page.querySelector('.page-intro').after(target);
  else page.append(target);
  const isCurrent = () => sequence === generation && id === localStorage.getItem("income.activePortfolioId");
  let state;
  try { state = await portfolioApi.onboarding(id); }
  catch {
    if (isCurrent()) target.innerHTML = '<div class="income-context"><h2>Explore no seu ritmo</h2><p>O guia está indisponível agora. Seus investimentos e operações continuam acessíveis.</p><a href="#operacoes" data-navigate class="income-button">Adicionar investimento</a></div>';
    return;
  }
  if (!isCurrent()) return;
  let viewed = state.current_step;
  const steps = [
    [empty ? "Adicione seu primeiro investimento." : "Mantenha seus investimentos em dia.",empty ? "Registre uma compra ou um investimento que você já possui. Seus dados começam com você." : "Registre novas movimentações para continuar acompanhando os investimentos que você cadastrou.",empty ? "Cadastrar investimento" : "Adicionar investimento","#operacoes"],
    ["Conheça a distribuição da sua carteira.","Veja como os valores disponíveis se distribuem entre classes de ativos.","Explorar composição",null],
    ["Explore o resultado dos seus investimentos.","Entenda a diferença entre patrimônio, resultado econômico e rentabilidade TWR.","Entender resultados","#entender"],
    ["Defina uma estratégia para acompanhar sua alocação.","Organize os pesos que você deseja acompanhar. Você decide seus próximos passos.","Ver estratégia","#estrategia"],
  ];
  function render() {
    if (!isCurrent()) return;
    if (state.status !== "ACTIVE") {
      target.innerHTML = `<div class="guidance-compact"><div><strong>${empty ? "Comece com seu primeiro investimento" : "Continue explorando sua carteira"}</strong><p>${empty ? "Adicione seus investimentos para acompanhar o patrimônio." : "Composição, resultados e estratégia estão disponíveis no seu ritmo."}</p></div><button type="button" class="income-button secondary" data-resume-guide>Retomar guia</button></div>`;
      target.querySelector('[data-resume-guide]').onclick = () => save({...state,status:"ACTIVE"});
      return;
    }
    const [title,copy,label,href] = steps[viewed-1];
    const markers = steps.map((_,i) => `<button type="button" aria-label="Etapa ${i+1}" ${i+1===viewed?'aria-current="step"':''} data-guide-step="${i+1}" ${i+1>state.current_step?'disabled':''}>${i+1}</button>`).join("");
    target.innerHTML = `<div class="income-context guidance-card"><div class="guidance-copy"><p class="income-eyebrow">${empty ? "Vamos começar" : "Explore no seu ritmo"} · ${viewed} de 4</p><h2>${title}</h2><p>${copy}</p>${href ? `<a class="income-button" href="${href}" data-navigate>${label}</a>` : '<button class="income-button" type="button" data-guide-allocation>Explorar composição</button>'}</div><div class="guidance-progress"><nav aria-label="Etapas do guia">${markers}</nav><div class="guidance-actions"><button class="income-button secondary" type="button" data-guide-skip>Pular por agora</button><button class="income-button secondary" type="button" data-guide-next>${viewed===4?'Concluir guia':'Continuar'}</button></div><p class="guidance-message" role="status" aria-live="polite"></p></div></div>`;
    target.querySelectorAll('[data-guide-step]').forEach(button => button.onclick = () => {viewed=Number(button.dataset.guideStep);render();});
    target.querySelector('[data-guide-skip]').onclick = () => save({...state,status:"SKIPPED"});
    target.querySelector('[data-guide-next]').onclick = () => save({current_step:Math.max(state.current_step,Math.min(viewed+1,4)),status:viewed===4?'COMPLETED':'ACTIVE'},Math.min(viewed+1,4));
    target.querySelector('[data-guide-allocation]')?.addEventListener('click',() => {
      if (empty) { target.querySelector('.guidance-message').textContent='Registre um investimento para visualizar sua composição.';return; }
      document.querySelector('[data-analysis-tab="1"]').click();
      document.querySelector('#portfolio-analysis').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});
    });
  }
  async function save(next, nextViewed=next.current_step) {
    if (!isCurrent()) return;
    target.querySelectorAll('button').forEach(button => button.disabled=true);
    try {
      const saved = await portfolioApi.saveOnboarding(id,next);
      if (!isCurrent()) return;
      state=saved;viewed=nextViewed;render();
    } catch {
      if (!isCurrent()) return;
      render();const message=target.querySelector('.guidance-message');
      if (message) message.textContent='Não foi possível salvar o progresso. Tente novamente.';
    }
  }
  render();
}
