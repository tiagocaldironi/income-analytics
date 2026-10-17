import { portfolioApi } from "../api.js?v=20260831-us-class-routing";
import { emptyState, errorState } from "../shared/ui.js";
import { formatDecimal } from "../shared/numbers.js";
let assetDiscoveryBound = false;

export function bindAssetDiscovery() {
  if (assetDiscoveryBound) return;
  const ticker = document.querySelector("#ticker");
  const details = document.querySelector("#asset-details");
  if (!ticker || !details) return;
  assetDiscoveryBound = true;
  details.insertAdjacentHTML("beforeend", '<div id="asset-suggestions" class="empty" aria-live="polite"></div>');
  const suggestions = document.querySelector("#asset-suggestions");
  const assetClass = document.querySelector("#trade-asset-class");
  const effectiveDate = document.querySelector("#effective-date");
  const eventType = document.querySelector("#event_type");
  let timer;
  let priceRequest = 0;
  let searchRequest = 0;
  const quoteContext = () => ({
    symbol: ticker.value.trim().toUpperCase(),
    date: effectiveDate?.value || "",
    assetClass: assetClass?.value || "",
  });
  const contextIsCurrent = context => {
    const current = quoteContext();
    return current.symbol === context.symbol
      && current.date === context.date
      && current.assetClass === context.assetClass;
  };
  const clearQuote = () => {
    priceRequest += 1;
    const price = document.querySelector("#unit_price");
    if (price) price.value = "";
  };
  const applyPrecision = candidate => {
    const crypto = candidate.suggested_asset_class === "CRYPTO";
    const quantity = document.querySelector("#quantity");
    const price = document.querySelector("#unit_price");
    quantity.type = crypto ? "text" : "number";
    price.type = crypto ? "text" : "number";
    quantity.inputMode = crypto ? "decimal" : "";
    price.inputMode = crypto ? "decimal" : "";
    if (crypto) {
      quantity.removeAttribute("min");
      quantity.removeAttribute("step");
      price.removeAttribute("min");
      price.removeAttribute("step");
    } else {
      quantity.min = "0.000001";
      quantity.step = "0.000001";
      price.min = "0.01";
      price.step = "0.01";
    }
    document.querySelector('label[for="quantity"]').textContent = crypto ? "Quantidade (até 8 casas)" : "Quantidade";
    document.querySelector('label[for="unit_price"]').textContent = `Preço unitário (${candidate.currency_code || "BRL"})`;
  };
  const fetchQuote = async context => {
    const variableIncomeClasses = [
      "BRAZILIAN_STOCK", "BRAZILIAN_ETF", "FII", "CRYPTO",
      "INTERNATIONAL", "INTERNATIONAL_ETF", "US_REIT",
    ];
    // A provento needs an asset identity only. It must not refresh or overwrite
    // its market quotation: receiving income is not a price-update event.
    if (eventType?.value !== "BUY") return;
    if (!context.symbol || !context.date || !variableIncomeClasses.includes(context.assetClass)) return;
    const requestId = ++priceRequest;
    suggestions.innerHTML = "<p>Atualizando cotação de " + context.symbol + " para " + context.date + "…</p>";
    try {
      const observation = await portfolioApi.automaticPriceForClass(
        context.symbol, context.date, context.assetClass,
      );
      if (requestId !== priceRequest || !contextIsCurrent(context)) return;
      if (!Number.isFinite(Number(observation.price)) || Number(observation.price) <= 0) throw new Error("Cotação inválida.");
      document.querySelector("#unit_price").value = context.assetClass === "CRYPTO"
        ? formatDecimal(observation.price, { minimumFractionDigits: 2, maximumFractionDigits: 8 })
        : String(observation.price);
      const source = observation.source === "b3_cotahist" ? "B3 COTAHIST" : observation.source;
      const quoteDate = context.assetClass === "CRYPTO" || observation.effective_date === context.date
        ? "Cotação de " + observation.effective_date
        : "Cotação do último pregão (" + observation.effective_date + ")";
      suggestions.innerHTML = "<p>" + quoteDate + " preenchida automaticamente via " + source + ".</p>";
    } catch {
      if (requestId !== priceRequest || !contextIsCurrent(context)) return;
      document.querySelector("#unit_price").value = "";
      suggestions.innerHTML = "<p>Não há cotação automática para esta data; informe o preço manualmente.</p>";
    }
  };
  const applyCandidate = candidate => {
    const usClasses = ["INTERNATIONAL", "INTERNATIONAL_ETF", "US_REIT"];
    if (usClasses.includes(assetClass?.value) && candidate.suggested_asset_class !== assetClass.value) {
      clearQuote();
      suggestions.innerHTML = errorState(
        "O ativo encontrado não corresponde à classe americana selecionada.",
      );
      return Promise.resolve();
    }
    ticker.value = candidate.symbol;
    ticker.dataset.assetName = candidate.name;
    document.querySelector("#trade-asset-class").value = candidate.suggested_asset_class || "OTHER";
    document.querySelector("#trade-asset-class").dispatchEvent(new Event("change"));
    document.querySelector("#country").value = candidate.country || "BR";
    document.querySelector("#currency-code").value = candidate.currency_code || "BRL";
    document.querySelector("#sector").value = candidate.sector || "";
    applyPrecision(candidate);
    return fetchQuote(quoteContext());
  };
  ticker.addEventListener("input", () => {
    clearTimeout(timer);
    clearQuote();
    ticker.dataset.assetName = "";
    const query = ticker.value.trim();
    if (query.length < 2) { suggestions.innerHTML = ""; return; }
    const requestId = ++searchRequest;
    timer = setTimeout(async () => {
      suggestions.innerHTML = "Buscando ativo…";
      try {
        const response = await portfolioApi.assetSearch(query, assetClass?.value || "");
        if (requestId !== searchRequest || ticker.value.trim() !== query) return;
        if (response.unavailable) { suggestions.innerHTML = emptyState("Busca automática indisponível. Continue com o cadastro manual."); return; }
        const exact = response.candidates.find(
          candidate => candidate.symbol.toUpperCase() === query.toUpperCase(),
        );
        if (exact) {
          await applyCandidate(exact);
          return;
        }
        const matching = response.candidates.filter(candidate => candidate.suggested_asset_class === assetClass?.value);
        const candidates = matching.length ? matching : response.candidates;
        const mismatchNote = !matching.length && candidates.length
          ? '<p class="hint">Nenhum resultado corresponde à classe escolhida. Ao selecionar um ativo, a classe detectada será aplicada.</p>'
          : "";
        suggestions.innerHTML = candidates.length
          ? mismatchNote + candidates.map(candidate => `<button type="button" class="secondary asset-candidate" data-candidate='${JSON.stringify(candidate)}'>${candidate.symbol} — ${candidate.name}<br><small>${candidate.instrument_type || "Ativo"} · Classe: ${candidate.suggested_asset_class || "OUTROS"} · ${candidate.currency_code || "—"}</small></button>`).join("")
          : emptyState("Nenhum ativo encontrado para a classe selecionada.");
      } catch (error) {
        if (requestId === searchRequest && ticker.value.trim() === query) suggestions.innerHTML = errorState(error);
      }
    }, 300);
  });
  effectiveDate?.addEventListener("change", () => {
    clearQuote();
    fetchQuote(quoteContext());
  });
  eventType?.addEventListener("change", () => {
    if (eventType.value !== "BUY") priceRequest += 1;
  });
  assetClass?.addEventListener("change", () => {
    clearQuote();
    applyPrecision({
      suggested_asset_class: assetClass.value,
      currency_code: document.querySelector("#currency-code")?.value,
    });
  });
  suggestions.addEventListener("click", event => {
    const button = event.target.closest(".asset-candidate");
    if (!button) return;
    const candidate = JSON.parse(button.dataset.candidate);
    applyCandidate(candidate);
  });
}
