import { portfolioApi } from "../api.js";
import { friendlyError, money } from "../shared/ui.js";

const style = document.createElement("style");
style.textContent = `.reserve-journey{max-width:900px;margin:0 auto}.reserve-steps{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;padding:0;margin:22px 0;list-style:none}.reserve-steps li{display:flex;align-items:center;gap:9px;color:var(--ia-text-secondary);font-size:.8rem}.reserve-steps li>span{display:grid;width:28px;height:28px;place-items:center;border:1px solid var(--ia-border);border-radius:50%}.reserve-steps li[aria-current=step]{color:var(--ia-brand);font-weight:700}.reserve-steps li[aria-current=step]>span{border-color:var(--ia-brand);background:#10b79f20}.reserve-step-card{padding:clamp(20px,4vw,36px);border:1px solid var(--ia-border);border-radius:14px;background:var(--ia-surface)}.reserve-step-card>header p{margin:0 0 6px;color:var(--ia-brand);font-size:.76rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase}.reserve-step-card>header h2{margin:0 0 20px}.reserve-copy>p,.reserve-next-steps>p{max-width:740px;line-height:1.6;color:var(--ia-text-secondary)}.reserve-info-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:22px 0}.reserve-info-grid article{padding:16px;border:1px solid var(--ia-border);border-radius:10px}.reserve-info-grid h3,.reserve-next-steps h3{margin:0 0 8px;font-size:.96rem}.reserve-info-grid p,.reserve-next-steps li{color:var(--ia-text-secondary);font-size:.86rem;line-height:1.55}.reserve-source-note{padding:12px 14px;border-left:2px solid var(--ia-brand);background:#0b1926;color:var(--ia-text-secondary);font-size:.82rem;line-height:1.55}.reserve-form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.reserve-form-grid label,.reserve-step-card>form>label{display:grid;gap:8px;font-weight:650}.reserve-form-grid small{color:var(--ia-text-secondary);font-weight:400}.reserve-goal-preview{display:flex;justify-content:space-between;gap:16px;align-items:center;margin:22px 0;padding:14px 0;border-top:1px solid var(--ia-border);border-bottom:1px solid var(--ia-border)}.reserve-progress-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:8px 0 20px}.reserve-progress-summary>div{display:grid;gap:5px;padding:13px;border:1px solid var(--ia-border);border-radius:9px}.reserve-progress-summary small{color:var(--ia-text-secondary)}.reserve-progress-track{height:10px;margin-top:18px;overflow:hidden;border-radius:99px;background:#26394b}.reserve-progress-track span{display:block;height:100%;border-radius:inherit;background:var(--ia-brand);transition:width .2s}.reserve-progress-label{color:var(--ia-brand);font-weight:700}.reserve-goal-reached,.reserve-goal-pending{padding:16px;border:1px solid var(--ia-border);border-radius:10px;background:#0d1b29}.reserve-goal-reached strong{color:var(--ia-brand)}.reserve-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:26px;padding-top:18px;border-top:1px solid var(--ia-border)}.reserve-actions button{min-width:120px}.reserve-error{color:#ff7883}.reserve-step-card form>label input{max-width:360px}@media(max-width:700px){.reserve-steps{gap:4px}.reserve-steps li{justify-content:center}.reserve-steps li small{display:none}.reserve-info-grid,.reserve-form-grid{grid-template-columns:1fr}.reserve-progress-summary{grid-template-columns:1fr}.reserve-goal-preview{align-items:flex-start;flex-direction:column}.reserve-step-card{padding:18px}.reserve-actions button{flex:1}}`;
document.head.append(style);

const escapeHtml = value => String(value ?? "").replace(/[&<>\'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
const numeric = value => Number.isFinite(Number(value)) ? Number(value) : 0;
let progress = null;
let busy = false;
let journeyError = "";

function percentage(value) {
  return `${numeric(value).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

function pageContent(step) {
  const steps = ["Entenda", "Defina sua meta", "Acompanhe", "Próximos passos"];
  const tracker = `<ol class="reserve-steps" aria-label="Etapas da jornada">${steps.map((label, index) => `<li${index + 1 === step ? ' aria-current="step"' : ""}><span>${index + 1}</span><small>${label}</small></li>`).join("")}</ol>`;
  const expenses = progress.essential_monthly_expenses ?? "";
  const months = progress.coverage_months ?? 6;
  const reserved = progress.declared_reserved_amount ?? "0";
  let body = "";
  if (step === 1) body = `<div class="reserve-copy"><p>A reserva de emergência ajuda a lidar com despesas inesperadas sem depender da venda de investimentos de longo prazo.</p><div class="reserve-info-grid"><article><h3>Acesso ao dinheiro</h3><p>Liquidez e prazo de resgate importam. A classe de um ativo, sozinha, não comprova quando o dinheiro estará disponível.</p></article><article><h3>Risco continua existindo</h3><p>Mesmo produtos de renda fixa podem ter riscos de crédito, mercado e liquidez. Nenhum investimento é automaticamente adequado.</p></article><article><h3>Uma meta pessoal</h3><p>O valor varia conforme despesas, estabilidade de renda, dependentes e outras fontes de proteção.</p></article></div><p class="reserve-source-note">A CVM apresenta 6 a 12 meses de despesas como referência educativa; não é uma regra universal nem uma recomendação individual.</p></div>`;
  if (step === 2) body = `<div class="reserve-form-grid"><label>Despesas essenciais mensais (R$)<input name="expenses" type="number" min="0" step="0.01" inputmode="decimal" value="${escapeHtml(expenses)}" required></label><label>Meses de cobertura<input name="months" type="number" min="1" max="60" step="1" value="${months}" required><small>Referência educativa: 6 a 12 meses. Ajuste conforme sua situação.</small></label></div><p class="reserve-goal-preview">Meta calculada <strong>${expenses === "" ? "Informe as despesas" : money(numeric(expenses) * numeric(months))}</strong></p>`;
  if (step === 3) {
    const goal = progress.reserve_goal === null ? null : numeric(progress.reserve_goal);
    const reservedValue = numeric(reserved);
    const pct = goal === null ? 0 : goal > 0 ? Math.min(100, reservedValue / goal * 100) : 100;
    const remaining = goal === null ? null : Math.max(0, goal - reservedValue);
    body = `<div class="reserve-progress-summary"><div><small>Meta declarada</small><strong data-reserve-goal>${goal === null ? "Ainda não definida" : money(goal)}</strong></div><div><small>Restante</small><strong data-reserve-remaining>${remaining === null ? "—" : money(remaining)}</strong></div><div><small>Cobertura</small><strong>${progress.months_covered === null ? "—" : `${numeric(progress.months_covered).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} meses`}</strong></div></div><label>Quanto você considera reservado? (R$)<input name="reserved" type="number" min="0" step="0.01" inputmode="decimal" value="${escapeHtml(reserved)}" required></label><div class="reserve-progress-track" role="progressbar" aria-label="Progresso declarado da reserva" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><span style="width:${pct}%"></span></div><p class="reserve-progress-label">${percentage(pct)} da meta · valor autodeclarado</p><p class="reserve-source-note">Esse valor não é importado da carteira nem validado como patrimônio pelo motor financeiro. Não representa ativo, operação ou aporte.</p>`;
  }
  if (step === 4) body = `<div class="reserve-next-steps">${progress.goal_reached ? `<div class="reserve-goal-reached"><strong>Você atingiu a meta que declarou.</strong><p>Revise o valor periodicamente quando suas despesas ou necessidades mudarem.</p></div>` : `<div class="reserve-goal-pending"><strong>${progress.reserve_goal === null ? "Sua meta ainda não está definida." : "Sua meta ainda não foi atingida."}</strong><p>Você pode atualizar despesas, meses de cobertura e valor reservado quando quiser.</p></div>`}<h3>Quando quiser avançar</h3><ul><li>Aprenda sobre diversificação e horizonte de investimento.</li><li>Reflita sobre sua tolerância e capacidade de suportar perdas.</li><li>Explore as estratégias do Income Starter somente quando modelos tiverem sido homologados e publicados.</li></ul><p>Esta jornada não aprova perfil de risco, não faz suitability e não recomenda automaticamente uma estratégia.</p><button class="secondary" type="button" data-review-reserve>Revisar minha meta</button></div>`;
  const back = step > 1 ? `<button type="button" class="secondary" data-reserve-back>Voltar</button>` : "";
  const next = step < 4 ? `<button type="submit" ${busy ? "disabled" : ""}>${busy ? "Salvando…" : step === 3 ? "Ver próximos passos" : "Continuar"}</button>` : "";
  const formStart = step < 4 ? '<form data-reserve-form>' : "";
  const formEnd = step < 4 ? "</form>" : "";
  return `${tracker}<article class="reserve-step-card"><header><p>Income Starter · Jornada educacional</p><h2>${steps[step - 1]}</h2></header>${formStart}${body}<p class="reserve-error" role="alert" aria-live="polite">${escapeHtml(journeyError)}</p><div class="reserve-actions">${back}${next}</div>${formEnd}</article>`;
}

function render() {
  const target = document.querySelector("#reserve-journey-workspace");
  if (!target || !progress) return;
  target.innerHTML = pageContent(progress.current_step);
  if (progress.current_step === 2) {
    const expenses = target.querySelector('[name="expenses"]');
    const months = target.querySelector('[name="months"]');
    const updateGoalPreview = () => {
      const preview = target.querySelector(".reserve-goal-preview strong");
      if (preview) preview.textContent = expenses.value === "" ? "Informe as despesas" : money(numeric(expenses.value) * numeric(months.value));
    };
    expenses.addEventListener("input", updateGoalPreview);
    months.addEventListener("input", updateGoalPreview);
  }
  if (progress.current_step === 3) {
    const reserved = target.querySelector('[name="reserved"]');
    reserved.addEventListener("input", () => {
      const goal = progress.reserve_goal === null ? null : numeric(progress.reserve_goal);
      const amount = Math.max(0, numeric(reserved.value));
      const value = goal === null ? 0 : goal > 0 ? Math.min(100, amount / goal * 100) : 100;
      const bar = target.querySelector('[role="progressbar"]');
      bar.setAttribute("aria-valuenow", String(value));
      bar.firstElementChild.style.width = `${value}%`;
      target.querySelector(".reserve-progress-label").textContent = `${percentage(value)} da meta · valor autodeclarado`;
      if (goal !== null) target.querySelector("[data-reserve-remaining]").textContent = money(Math.max(0, goal - amount));
    });
  }
  target.querySelector("[data-review-reserve]")?.addEventListener("click", () => {
    progress.current_step = 2;
    journeyError = "";
    render();
  });
  target.querySelector("[data-reserve-back]")?.addEventListener("click", async () => {
    const previousStep = progress.current_step;
    progress.current_step -= 1;
    await persist(previousStep);
  });
  target.querySelector("form")?.addEventListener("submit", async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (progress.current_step === 2) {
      progress.essential_monthly_expenses = String(form.get("expenses"));
      progress.coverage_months = Number(form.get("months"));
      if (progress.coverage_months < 1 || progress.coverage_months > 60) return;
    } else if (progress.current_step === 3) {
      progress.declared_reserved_amount = String(form.get("reserved"));
    }
    const previousStep = progress.current_step;
    progress.current_step += 1;
    await persist(previousStep);
  });
}

async function persist(previousStep) {
  if (busy) return;
  journeyError = "";
  busy = true;
  render();
  try {
    progress = await portfolioApi.saveReserveJourney({
      essential_monthly_expenses: progress.essential_monthly_expenses,
      coverage_months: progress.coverage_months,
      declared_reserved_amount: progress.declared_reserved_amount,
      current_step: progress.current_step,
    });
  } catch (error) {
    journeyError = friendlyError(error);
    progress.current_step = previousStep;
  } finally {
    busy = false;
    render();
  }
}

export async function loadReserveJourney() {
  const target = document.querySelector("#reserve-journey-workspace");
  if (!target) return;
  target.innerHTML = `<div class="empty">Carregando seu progresso…</div>`;
  try {
    progress = await portfolioApi.reserveJourney();
    render();
  } catch (error) {
    console.error("Falha ao carregar a jornada Income Starter", error);
    target.innerHTML = `<div class="empty reserve-error" role="alert"><p>Não foi possível carregar a jornada Income Starter.</p><small>${escapeHtml(friendlyError(error))}</small><p><button class="secondary" type="button" data-retry-reserve> Tentar novamente </button></p></div>`;
    target.querySelector("[data-retry-reserve]").addEventListener("click", loadReserveJourney);
  }
}
