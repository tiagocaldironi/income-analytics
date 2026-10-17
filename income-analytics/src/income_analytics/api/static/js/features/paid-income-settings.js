import { portfolioApi } from "../api.js";
import { friendlyError, setMessage, withProcessing } from "../shared/ui.js";

const labels = { DISABLED: "Desativada", TOKEN_MISSING: "Token não configurado", CONNECTED: "Conectada", PLAN_NOT_SUPPORTED: "Seu plano BRAPI não possui acesso a proventos", AUTH_ERROR: "Token inválido", RATE_LIMITED: "Limite de requisições atingido", PROVIDER_ERROR: "Erro de comunicação" };

export async function bindPaidIncomeSettings() {
  const target = document.querySelector("#paid-income-settings");
  if (!target) return;
  try {
    const settings = await portfolioApi.paidIncomeSettings();
    target.innerHTML = '<h2>Proventos automáticos</h2><p>Provider: BRAPI. Apenas proventos já pagos são importados.</p><label><input type="checkbox" id="paid-income-enabled"' + (settings.enabled ? " checked" : "") + '> Importar proventos automaticamente via BRAPI</label><label>Token BRAPI<input id="paid-income-token" type="password" autocomplete="new-password" placeholder="' + (settings.token_configured ? "Token configurado" : "Informe o token") + '"></label><p>Status: <strong>' + (labels[settings.status] || settings.status) + '</strong></p><p>Última sincronização: ' + (settings.last_sync_at ? new Date(settings.last_sync_at).toLocaleString("pt-BR") : "Nunca") + '</p><button type="button" id="paid-income-save">Salvar</button> <button type="button" class="secondary" id="paid-income-test">Testar conexão</button> <button type="button" class="secondary" id="paid-income-sync"' + (settings.enabled ? "" : " disabled") + '>Sincronizar agora</button><div class="message" id="paid-income-message" role="alert"></div>';
    const message = target.querySelector("#paid-income-message");
    target.querySelector("#paid-income-save").addEventListener("click", async event => {
      try {
        await withProcessing(event.currentTarget, () => portfolioApi.updatePaidIncomeSettings({ enabled: target.querySelector("#paid-income-enabled").checked, api_token: target.querySelector("#paid-income-token").value || undefined }), "Salvando…");
        target.querySelector("#paid-income-token").value = "";
        setMessage(message, "Configuração salva.");
      } catch (error) { setMessage(message, friendlyError(error), "error"); }
    });
    target.querySelector("#paid-income-test").addEventListener("click", async event => {
      try { const result = await withProcessing(event.currentTarget, portfolioApi.testPaidIncome, "Testando…"); setMessage(message, labels[result.status] || result.status); } catch (error) { setMessage(message, friendlyError(error), "error"); }
    });
    target.querySelector("#paid-income-sync").addEventListener("click", async event => {
      try { const result = await withProcessing(event.currentTarget, portfolioApi.syncPaidIncome, "Sincronizando…"); setMessage(message, (labels[result.status] || result.status) + ". " + (result.imported || 0) + " evento(s) importado(s)."); } catch (error) { setMessage(message, friendlyError(error), "error"); }
    });
  } catch (error) { target.textContent = friendlyError(error); }
}
