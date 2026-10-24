import { portfolioApi } from "../api.js";
import { icon } from "../shared/icons.js";
let generation=0, state=null, dashboard=null, bound=false, choosingIntent=false, pendingOperation=null, lastWallet=null;
const esc=value=>String(value??"").replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const activeWallet=()=>localStorage.getItem("income.activePortfolioId");
const button=(label,action,secondary=false)=>`<button type="button" class="income-button${secondary?' secondary':''}" data-onboarding-action="${action}">${label}</button>`;
export function portfolioIsEmpty(data) {
  const hasAssets = data.holdings.classes.some(group => group.assets.some(asset => !asset.target_only));
  const boundary = data.history?.history_boundary || data.portfolio.history_boundary;
  // The read model may emit a zero baseline snapshot even without any events.
  const hasHistory = boundary?.source === "NO_OBSERVED_FINANCIAL_EVENTS" ? false : Boolean(data.history?.snapshots?.length);
  return !hasAssets && !hasHistory &&
    ![data.portfolio.total_market_value,data.portfolio.total_contributions,data.portfolio.income_received,data.portfolio.cash].some(value => Number(value || 0) !== 0);
}

export function invalidatePortfolioGuidance(){
  generation++;state=null;dashboard=null;
  if(lastWallet!==activeWallet())choosingIntent=false;
  if(pendingOperation!==activeWallet())pendingOperation=null;
  const target=document.querySelector('#portfolio-guidance');
  if(target){target.replaceChildren();target.hidden=true;}
  const assist=document.querySelector('#onboarding-operation-help');if(assist&&!pendingOperation)assist.remove();
}
function current(id,sequence){return id===activeWallet()&&sequence===generation;}
function error(message){const target=document.querySelector('#portfolio-guidance');if(!target)return;target.hidden=false;target.innerHTML=`<div class="income-context" role="alert"><p>${esc(message)}</p>${button('Tentar novamente','retry',true)}<a href="#operacoes" class="income-button secondary" data-navigate>Registrar investimento</a></div>`;}
export async function renderPortfolioGuidance(data){
  bind();dashboard=data;
  const target=document.querySelector('#portfolio-guidance');if(!target)return;
  const id=activeWallet(),sequence=++generation;lastWallet=id;
  const page=document.querySelector('[data-page="minha-carteira"]');page.dataset.empty=String(portfolioIsEmpty(data));
  page.querySelector('.page-intro').after(target);
  target.hidden=false;target.innerHTML='<div class="onboarding-skeleton" role="status" aria-label="Carregando seus primeiros passos"></div>';
  try{
    let next=await portfolioApi.contextualOnboarding(id);
    if(!current(id,sequence))return;
    if(next.status==='ACTIVE')next=await portfolioApi.saveContextualOnboarding(id,{action:'START'});
    if(!current(id,sequence))return;
    state=next;render();
  }catch{if(current(id,sequence))error('Não foi possível carregar seus primeiros passos. Seus investimentos continuam disponíveis.');}
}
async function save(body){
  if(!state)return false;
  const id=state.portfolio_id,sequence=generation;
  if(id!==activeWallet())return false;
  const restoreFocus=Boolean(document.querySelector('#portfolio-guidance')?.contains?.(document.activeElement));
  document.querySelectorAll('#portfolio-guidance button').forEach(node=>node.disabled=true);
  try{
    const next=await portfolioApi.saveContextualOnboarding(id,body);
    if(!current(id,sequence))return false;
    state=next;choosingIntent=false;render();if(restoreFocus){const heading=document.querySelector('#onboarding-title');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}}return true;
  }catch{
    if(current(id,sequence)){render();const msg=document.querySelector('#onboarding-message');if(msg)msg.textContent='Não foi possível salvar. Tente novamente; seu progresso não foi confirmado.';}
    return false;
  }
}

export function setupContextualOnboarding(){bind();}
export function renderOnboardingAchievements(achievements){
  return `<ol class="onboarding-achievements" aria-label="Suas conquistas">${achievements.map(a=>`<li data-achievement-state="${a.state}"><span aria-hidden="true">${icon(a.state==='COMPLETED'?'check':a.id==='wallet_created'?'wallet':a.id==='first_investment'?'plus':'chart')}</span><div><strong>${esc(a.title)}</strong><small>${esc(a.description)}</small><small>${esc(a.state==='COMPLETED'?'Concluído':a.state==='IN_PROGRESS'?'Em andamento':'Ainda não iniciado')}</small></div></li>`).join('')}</ol>`;
}
function render(){
  const target=document.querySelector('#portfolio-guidance');if(!target||!state||state.portfolio_id!==activeWallet())return;
  if(state.status!=='ACTIVE'&&!choosingIntent){target.hidden=true;target.replaceChildren();return;}
  target.hidden=false;
  const intent=state.ask_intent||choosingIntent;
  const progress=renderOnboardingAchievements(state.achievements);
  let content='';
  if(intent){
    content=`<h2 id="onboarding-title">Como você quer começar no Income?</h2><p>Vamos adaptar seus primeiros passos. Você pode mudar sua escolha quando quiser.</p><fieldset class="onboarding-intents"><legend class="sr-only">Escolha como começar</legend>${[['STARTING','book','Estou começando a investir','Quero aprender o básico e organizar meus primeiros objetivos.'],['EXISTING','wallet','Já tenho investimentos','Quero reunir meus investimentos e acompanhar meu patrimônio.'],['ORGANIZE','layers','Quero organizar meu patrimônio','Tenho investimentos diferentes e quero enxergar tudo em um só lugar.']].map(([code,i,title,copy])=>`<label>${icon(i)}<input type="radio" name="onboarding-intent" value="${code}" ${state.intent===code?'checked':''}><span><strong>${title}</strong><small>${copy}</small></span></label>`).join('')}</fieldset><p class="onboarding-note">Essa escolha personaliza o uso do Income. Não define seu perfil de risco.</p><div class="onboarding-actions">${button('Continuar','intent')}${button('Agora não','defer',true)}</div>`;
  }else if(state.last_step===2){
    content=`<h2 id="onboarding-title">Sua carteira está pronta!</h2><p><strong>${esc(state.portfolio_name)}</strong></p><p>Agora vamos adicionar seu primeiro investimento. Pode começar por qualquer ativo que você já tenha.</p>${state.intent==='STARTING'?'<p>Se preferir, conheça o básico na jornada educacional Primeiros Passos.</p><a href="#primeiros-passos" data-navigate class="income-button secondary">Conhecer Primeiros Passos</a>':''}<div class="onboarding-actions">${button('Adicionar meu primeiro investimento','classes')}${button('Fazer isso depois','skip',true)}</div>`;
  }else if(state.last_step===3){
    content=`<h2 id="onboarding-title">Por onde você quer começar?</h2><p>Escolha um tipo de investimento. Você poderá adicionar outros depois.</p><div class="onboarding-classes">${state.classes.map(c=>`<button type="button" data-onboarding-class="${esc(c.code)}">${icon(c.code==='FIXED_INCOME'?'income':c.code==='REAL_ESTATE'?'home':'layers')}<span>${esc(c.label)}</span></button>`).join('')}</div><div class="onboarding-actions">${button('Voltar','ready',true)}${button('Pular por enquanto','skip',true)}</div>`;
  }else if(state.last_step===4){
    content=`<h2 id="onboarding-title">Vamos registrar seu investimento</h2><p>Informe os dados que você já conhece. O Income organizará as informações da sua carteira.</p><p>Usamos o mesmo cadastro e as mesmas validações das operações da sua carteira.</p><div class="onboarding-actions">${button('Abrir cadastro','register')}${button('Voltar','classes',true)}${button('Fazer isso depois','skip',true)}</div>`;
  }else if(state.last_step===5){
    content=`<h2 id="onboarding-title">Seu primeiro investimento já está no Income!</h2><p>Agora você pode acompanhar esse investimento e continuar montando sua carteira no seu ritmo.</p><div class="onboarding-actions">${button('Ver minha carteira','analysis')}${button('Adicionar outro investimento','classes',true)}</div>`;
  }else{
    content=`<h2 id="onboarding-title">Agora vamos conhecer sua carteira?</h2><p>Veja o que já conseguimos mostrar com os investimentos cadastrados.</p>${state.facts.available_analyses.length?'':'<p>Algumas análises aparecerão conforme você registrar mais informações e construir seu histórico.</p>'}<div class="onboarding-actions">${state.facts.available_analyses.length?button('Explorar primeira análise','explore'):button('Adicionar informações','classes')}${button('Continuar depois','skip',true)}</div>`;
  }
  target.innerHTML=`<section class="income-context onboarding-card" aria-labelledby="onboarding-title"><p class="income-eyebrow">Seus primeiros passos · Income Free</p>${content}${progress}<div class="onboarding-footer">${button('Mudar minha escolha','change-intent',true)}${button('Dispensar guia','dismiss',true)}</div><p id="onboarding-message" role="status" aria-live="polite"></p></section>`;
}
function openRegistration(){
  if(!state||state.portfolio_id!==activeWallet())return;
  pendingOperation=state.portfolio_id;
  window.dispatchEvent(new CustomEvent('income:open-operation',{detail:{assetClass:state.selected_class,eventType:'BUY'}}));
  const dialog=document.querySelector('#operation-modal');
  if(dialog?.open){
    document.querySelector('#onboarding-operation-help')?.remove();
    const help=document.createElement('p');help.id='onboarding-operation-help';help.className='onboarding-note';
    help.textContent=['FIXED_INCOME','PENSION','REAL_ESTATE'].includes(state.selected_class)?'Preencha os campos específicos deste investimento. Confira a data e o valor aplicado conforme seus registros.':'Quantidade: quantas unidades foram negociadas? Data: quando a operação aconteceu? Preço unitário: quanto você pagou por unidade?';
    dialog.querySelector('#trade-form')?.prepend(help);
  }
}
function bind(){
  if(bound)return;bound=true;
  document.querySelector('#operation-modal')?.addEventListener('close',()=>{pendingOperation=null;document.querySelector('#onboarding-operation-help')?.remove();});
  document.addEventListener('change',event=>{
    if(event.target.id!=='trade-asset-class')return;
    const help=document.querySelector('#onboarding-operation-help');
    if(help)help.textContent=['FIXED_INCOME','PENSION','REAL_ESTATE'].includes(event.target.value)?'Preencha os campos específicos deste investimento. Confira a data e o valor aplicado conforme seus registros.':'Quantidade: quantas unidades foram negociadas? Data: quando a operação aconteceu? Preço unitário: quanto você pagou por unidade?';
  });
  const help=document.querySelector('[data-page="ajuda-metodologia"] .page-intro');
  if(help&&!document.querySelector('[data-reopen-onboarding]'))help.insertAdjacentHTML('beforeend','<button type="button" class="income-button secondary" data-reopen-onboarding>Retomar primeiros passos</button>');
  document.addEventListener('click',async event=>{
    const reopen=event.target.closest('[data-reopen-onboarding]');
    if(reopen){
      const id=activeWallet(),sequence=++generation;
      try{const next=await portfolioApi.saveContextualOnboarding(id,{action:'RESUME'});if(!current(id,sequence))return;state=next;choosingIntent=false;location.hash='#minha-carteira';render();}catch{location.hash='#minha-carteira';error('Não foi possível retomar seus primeiros passos.');}
      return;
    }
    const selected=event.target.closest('[data-onboarding-class]');
    if(selected){if(await save({action:'CLASS',asset_class:selected.dataset.onboardingClass}))openRegistration();return;}
    const action=event.target.closest('[data-onboarding-action]')?.dataset.onboardingAction;
    if(action){
      if(action==='retry'){if(dashboard)renderPortfolioGuidance(dashboard);return;}
      if(action==='intent'){const intent=document.querySelector('[name="onboarding-intent"]:checked')?.value;if(!intent){document.querySelector('#onboarding-message').textContent='Escolha uma das opções para continuar.';return;}await save({action:'INTENT',intent});}
      if(action==='defer')await save({action:'DEFER_INTENT'});
      if(action==='change-intent'){choosingIntent=true;render();}
      if(action==='classes')await save({action:'STEP',step:3});
      if(action==='ready')await save({action:'STEP',step:2});
      if(action==='analysis')await save({action:'STEP',step:6});
      if(action==='skip')await save({action:'SKIP'});
      if(action==='dismiss')await save({action:'DISMISS'});
      if(action==='register')openRegistration();
      if(action==='explore'&&state?.facts.available_analyses.length){const analysis=state.facts.available_analyses[0];const tab=document.querySelector(`[data-analysis-tab="${analysis==='composition'?1:0}"]`);tab?.focus();tab?.click();document.querySelector('#portfolio-analysis')?.scrollIntoView({block:'start'});}
    }
  });
  document.addEventListener('income:analysis-explored',async event=>{
    if(state?.status!=='ACTIVE')return;
    const analysis=event.detail?.index===1?'composition':event.detail?.index===0?'evolution':null;
    if(state.facts.available_analyses.includes(analysis))await save({action:'EXPLORE',analysis});
  });
  window.addEventListener('income:operation-confirmed',async event=>{
    if(event.detail?.portfolioId!==pendingOperation||pendingOperation!==activeWallet())return;
    pendingOperation=null;document.querySelector('#onboarding-operation-help')?.remove();
    if(await save({action:'CONFIRM_ASSET'}))document.querySelector('#portfolio-guidance')?.scrollIntoView({block:'start'});
  });
}
