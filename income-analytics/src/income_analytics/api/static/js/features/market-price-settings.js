import { portfolioApi } from "../api.js";
import { renderDataSources } from "./data-sources.js";
import { friendlyError, setMessage, withProcessing } from "../shared/ui.js";

let bound = false;

function appendLine(parent, tag, text, className = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  parent.append(element);
  return element;
}

async function renderRefreshHistory(container) {
  container.replaceChildren();
  appendLine(container, "p", "Carregando histórico…");
  const { runs = [] } = await portfolioApi.marketPriceRefreshRuns(20);
  container.replaceChildren();
  if (!runs.length) {
    appendLine(container, "p", "Nenhuma atualização registrada.");
    return;
  }
  for (const run of runs) {
    const article = document.createElement("article");
    article.className = "refresh-run";
    const timestamp = new Date(run.started_at).toLocaleString("pt-BR");
    appendLine(article, "h4", timestamp + " · " + run.status);
    for (const provider of run.providers || []) {
      appendLine(
        article,
        "p",
        provider.provider + " · " + provider.status + " · "
          + (provider.resolved_assets || 0) + " cotação(ões) atualizada(s)",
        "refresh-run-provider",
      );
      for (const error of provider.errors || []) {
        const subject = error.asset ? error.asset + " · " : "";
        appendLine(
          article,
          "p",
          subject + (error.stage || "erro") + " · " + (error.error_type || "Error")
            + ": " + (error.message || "Sem mensagem detalhada."),
          "refresh-run-error",
        );
      }
      for (const warning of provider.warnings || []) {
        appendLine(
          article,
          "p",
          "Aviso " + (warning.stage || "provider") + " · "
            + (warning.error_type || "Warning") + ": "
            + (warning.message || "Sem mensagem detalhada."),
          "refresh-run-warning",
        );
      }
    }
    container.append(article);
  }
}

export function bindMarketPriceSettings() {
  const button = document.querySelector("#settings-refresh-prices");
  const message = document.querySelector("#settings-refresh-prices-message");
  const historyButton = document.querySelector("#settings-refresh-price-history");
  const history = document.querySelector("#settings-refresh-price-runs");
  if (!button || !message || bound) return;
  bound = true;

  historyButton?.addEventListener("click", async () => {
    try {
      await renderRefreshHistory(history);
    } catch (error) {
      history.replaceChildren();
      appendLine(history, "p", friendlyError(error), "refresh-run-error");
    }
  });

  button.addEventListener("click", async () => {
    try {
      const result = await withProcessing(
        button,
        () => portfolioApi.refreshPrices(),
        "Consultando fontes…",
      );
      const unchanged = result.skipped?.length || 0;
      const unavailable = result.unavailable?.length || 0;
      const unavailableAssets = (result.unavailable || []).join(", ");
      const failedProviders = (result.providers || [])
        .filter(provider => ["FAILED", "PARTIAL", "DEGRADED"].includes(provider.status))
        .length;
      const details = [
        unavailableAssets ? "Sem cotação: " + unavailableAssets + "." : "",
        failedProviders
          ? failedProviders + " fonte(s) tiveram falhas ou usaram fallback; consulte o histórico para ver o erro."
          : "",
      ].filter(Boolean).join(" ");
      const type = unavailable || failedProviders ? "error" : "success";
      setMessage(
        message,
        (result.updated || 0) + " cotação(ões) atualizada(s), " + unchanged
          + " sem alteração e " + unavailable + " indisponível(is). " + details,
        type,
      );
      await renderDataSources();
      if (history) await renderRefreshHistory(history);
    } catch (error) {
      setMessage(message, friendlyError(error), "error");
      if (history) {
        try {
          await renderRefreshHistory(history);
        } catch {
          // The refresh error remains visible; the history can be loaded separately.
        }
      }
    }
  });
}
