export const money = (value, currency = "BRL") => new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format(Number(value));
export const percentage = value => `${Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;
export const percentagePoints = value => `${value >= 0 ? "+" : ""}${Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} p.p.`;
export const date = value => value ? new Intl.DateTimeFormat("pt-BR").format(new Date(`${value}T00:00:00`)) : "—";
export const table = (headers, rows) => `<div class="table-wrap"><table><thead><tr>${headers.map(header => `<th>${header}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
export const emptyState = (message, action = "") => `<div class="empty"><p>${message}</p>${action}</div>`;
export const errorState = message => `<div class="message message-error" role="alert">${friendlyError(message)}</div>`;
export const loadingState = "<p class=\"empty\" aria-busy=\"true\">Carregando…</p>";

export function friendlyError(error) {
  const message = typeof error === "string" ? error : error?.message || "";
  if (/insufficient|quantidade insuficiente/i.test(message)) return "Quantidade insuficiente para concluir esta operação.";
  if (/not found|não encontrado/i.test(message)) return "O item informado não foi encontrado.";
  if (/validation|invalid|obrigatório|maior que/i.test(message)) return message;
  if (message && !/internal server error|failed to fetch|networkerror/i.test(message)) return message;
  return "Não foi possível concluir a ação. Verifique os dados e tente novamente.";
}

export function setMessage(target, message, type = "success") {
  target.textContent = message;
  target.className = `message message-${type}`;
}

export async function withProcessing(button, task, label = "Salvando…") {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = label;
  try { return await task(); } finally { button.disabled = false; button.textContent = original; }
}

export function validateForm(form) {
  if (form.checkValidity()) return true;
  form.reportValidity();
  return false;
}

export function confirmDangerousAction() {
  return new Promise(resolve => {
    const dialog = document.createElement("dialog");
    dialog.className = "confirm-dialog";
    dialog.innerHTML = "<form method=\"dialog\"><h2>Excluir todos os dados?</h2><p>Serão removidos ativos, operações, preços, políticas, targets, histórico e demais dados locais. Esta ação não pode ser desfeita.</p><label for=\"reset-confirmation\">Digite EXCLUIR para continuar</label><input id=\"reset-confirmation\" autocomplete=\"off\"><div class=\"dialog-actions\"><button value=\"cancel\" class=\"secondary\">Cancelar</button><button value=\"confirm\" class=\"destructive\">Excluir dados</button></div></form>";
    dialog.addEventListener("close", () => { resolve(dialog.returnValue === "confirm" && dialog.querySelector("#reset-confirmation").value === "EXCLUIR"); dialog.remove(); });
    document.body.append(dialog);
    dialog.showModal();
  });
}

export function confirmOperationDeletion() {
  return new Promise(resolve => {
    const dialog = document.createElement("dialog");
    dialog.className = "confirm-dialog operation-delete-dialog";
    dialog.innerHTML = '<form method="dialog"><h2>Excluir lançamento?</h2><p>Esta operação será removida permanentemente. A carteira, os resultados e os gráficos serão recalculados imediatamente.</p><div class="dialog-actions"><button value="cancel" class="secondary">Cancelar</button><button value="confirm" class="destructive">Excluir lançamento</button></div></form>';
    dialog.addEventListener("close", () => { resolve(dialog.returnValue === "confirm"); dialog.remove(); });
    document.body.append(dialog);
    dialog.showModal();
  });
}
