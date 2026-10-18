import { portfolioApi } from "../api.js?v=20261004-operations-refinement-v2";
import { confirmDangerousAction, confirmOperationDeletion, emptyState, friendlyError, money, setMessage, table, validateForm, withProcessing } from "../shared/ui.js";
import { decimalForApi, isPositiveDecimal } from "../shared/numbers.js";
import { loadPortfolio } from "./portfolio.js";
let operationsBound = false;

function setOperationFields(type) {
  const external = ["DEPOSIT", "WITHDRAWAL"].includes(type);
  const dividend = type === "DIVIDEND";
  const jcp = type === "INTEREST_ON_EQUITY";
  const income = dividend || jcp;
  const assetClass = document.querySelector("#trade-asset-class")?.value;
  const fixedIncome = type === "BUY" && assetClass === "FIXED_INCOME";
  const fixedIncomeSale = type === "SELL" && assetClass === "FIXED_INCOME";
  const pension = type === "BUY" && assetClass === "PENSION";
  const realEstate = type === "BUY" && assetClass === "REAL_ESTATE";
  const wealth = fixedIncome || pension || realEstate;
  document.querySelector("#asset-details").hidden = external || wealth;
  document.querySelector("#asset-class-details").hidden = external;
  const assetClassLabel = document.querySelector('label[for="trade-asset-class"]');
  if (assetClassLabel) assetClassLabel.textContent = type === "SELL" ? "Classe do ativo" : "Classe do ativo (no primeiro lançamento)";
  const tickerLabel = document.querySelector('label[for="ticker"]');
  if (tickerLabel) tickerLabel.textContent = fixedIncomeSale ? "Ativo da carteira" : "Ativo";
  document.querySelector("#ticker").maxLength = fixedIncomeSale ? 64 : 12;
  const capitalFlow = document.querySelector("#capital-flow-details");
  if (capitalFlow) capitalFlow.hidden = (type !== "BUY" && !external) || wealth;
  ["#country", "#currency-code", "#sector"].forEach(selector => {
    const input = document.querySelector(selector);
    const hide = external || wealth || fixedIncomeSale || (selector === "#sector" && fixedIncome);
    input.hidden = hide;
    input.previousElementSibling.hidden = hide;
    const label = document.querySelector('label[for="' + input.id + '"]');
    if (label) {
      label.hidden = hide;
      label.style.display = hide ? "none" : "";
    }
  });
  const effectiveDate = document.querySelector("#effective-date");
  const effectiveDateLabel = document.querySelector('label[for="effective-date"]');
  const hideEffectiveDate = pension;
  if (effectiveDate) {
    effectiveDate.hidden = hideEffectiveDate;
    effectiveDate.required = !hideEffectiveDate;
  }
  if (effectiveDateLabel) {
    effectiveDateLabel.hidden = hideEffectiveDate;
    effectiveDateLabel.style.display = hideEffectiveDate ? "none" : "";
    effectiveDateLabel.textContent = realEstate ? "Data da avaliação" : "Data";
  }
  document.querySelector("#trade-details").hidden = external || income || wealth || fixedIncomeSale;
  document.querySelector("#fixed-income-sale-details").hidden = !fixedIncomeSale;
  document.querySelector("#dividend-details").hidden = !dividend;
  document.querySelector("#jcp-details").hidden = !jcp;
  document.querySelector("#external-flow-details").hidden = !external;
  document.querySelector("#fixed-income-details").hidden = !fixedIncome;
  document.querySelector("#pension-details").hidden = !pension;
  document.querySelector("#real-estate-details").hidden = !realEstate;
  ["#fixed-income-details", "#pension-details", "#real-estate-details"].forEach(selector => {
    const active = document.querySelector(selector);
    active?.querySelectorAll("input, select").forEach(input => { input.disabled = active.hidden; });
    active?.querySelectorAll("[hidden] input, [hidden] select").forEach(input => {
      input.disabled = true;
      input.required = false;
    });
  });
  if (realEstate) {
    ["#wealth-ticker", "#wealth-name", "#property-description"].forEach(selector => {
      const input = document.querySelector("#real-estate-details " + selector);
      const label = input?.closest("label");
      if (label) {
        label.hidden = true;
        label.style.display = "none";
      }
      if (input) {
        input.disabled = true;
        input.required = false;
      }
    });
    [
      "#property-type", "#property-cep", "#property-country", "#property-state",
      "#property-city", "#property-address", "#property-acquisition-date",
      "#property-acquisition-value", "#property-ownership", "#property-value",
    ].forEach(selector => {
      const input = document.querySelector("#real-estate-details " + selector);
      if (input) {
        input.disabled = false;
        input.required = true;
      }
    });
  }
  document.querySelector("#ticker").required = (!external && !wealth) || fixedIncomeSale;
  document.querySelector("#quantity").required = !external && !income && !wealth && !fixedIncomeSale;
  document.querySelector("#unit_price").required = !external && !income && !wealth && !fixedIncomeSale;
  document.querySelector("#fixed-income-sale-value").required = fixedIncomeSale;
  document.querySelector("#dividend-amount").required = dividend;
  document.querySelector("#jcp-gross").required = jcp;
  document.querySelector("#jcp-tax").required = jcp;
  document.querySelector("#external-flow-amount").required = external;
  if (fixedIncome) setFixedIncomeFields();
  if (pension) setPensionFields();
}

function wealthPayload(type) {
  const scope = document.querySelector(
    type === "FIXED_INCOME" ? "#fixed-income-details" : type === "PENSION" ? "#pension-details" : "#real-estate-details"
  );
  const value = id => scope?.querySelector(id)?.value || "";
  if (type === "FIXED_INCOME") {
    const indexer = value("#fi-indexer");
    const name = value("#wealth-name");
    return {
      ticker: fixedIncomeLotTicker(name),
      name, instrument_type: value("#fi-instrument"), indexer_type: indexer,
      application_date: document.querySelector("#effective-date").value, principal_amount: value("#fi-principal"),
      contracted_rate: indexer === "PREFIXED" ? value("#fi-rate") : null,
      percentage_of_indexer: ["CDI_PERCENT", "CDI_PLUS"].includes(indexer)
        ? value("#fi-percentage")
        : null,
      spread: ["CDI_PLUS", "IPCA_PLUS"].includes(indexer) ? value("#fi-spread") : null,
    };
  }
  if (type === "PENSION") {
    const bool = id => value(id) === "" ? null : value(id) === "true";
    return {
      plan_name: value("#pension-name"),
      institution: value("#pension-institution"),
      institution_cnpj: value("#pension-cnpj") || null,
      ownership_origin: value("#pension-origin"),
      pension_system_type: value("#pension-system"),
      product_type: value("#pension-system") === "OPEN" ? value("#pension-product") : null,
      closed_plan_modality: value("#pension-system") === "CLOSED" ? value("#pension-modality") : null,
      susep_process_number: value("#pension-system") === "OPEN" ? value("#pension-susep") || null : null,
      cnpb: value("#pension-system") === "CLOSED" ? value("#pension-cnpb") || null : null,
      tax_regime: value("#pension-tax"),
      start_date: value("#pension-balance-date"),
      reported_balance: value("#pension-balance"),
      reported_balance_date: value("#pension-balance-date"),
      participant_balance: value("#pension-composition") ? value("#pension-participant-balance") : null,
      sponsor_balance: value("#pension-composition") ? value("#pension-sponsor-balance") : null,
      sponsor_name: ["EMPLOYER", "ASSOCIATION"].includes(value("#pension-origin")) ? value("#pension-sponsor-name") || null : null,
      sponsor_cnpj: ["EMPLOYER", "ASSOCIATION"].includes(value("#pension-origin")) ? value("#pension-sponsor-cnpj") || null : null,
      employer_match_enabled: value("#pension-origin") === "EMPLOYER" ? bool("#pension-match-enabled") : null,
      employer_match_rate: value("#pension-match-enabled") === "true" ? value("#pension-match-rate") || null : null,
      match_limit: value("#pension-match-enabled") === "true" ? value("#pension-match-limit") || null : null,
      match_rule_notes: value("#pension-match-enabled") === "true" ? value("#pension-match-notes") || null : null,
      vesting_enabled: value("#pension-origin") === "EMPLOYER" ? bool("#pension-vesting-enabled") : null,
      current_vested_percentage: value("#pension-vesting-enabled") === "true" ? value("#pension-vested-percentage") || null : null,
      vesting_rule_notes: value("#pension-vesting-enabled") === "true" ? value("#pension-vesting-notes") || null : null,
      vehicle_cnpj: value("#pension-vehicle-cnpj") || null,
      vehicle_name: value("#pension-vehicle-name") || null,
    };
  }
  const propertyType = value("#property-type");
  const city = value("#property-city");
  const cep = value("#property-cep").replace(/\D/g, "");
  const propertyCode = {
    APARTMENT: "APT",
    HOUSE: "HOUSE",
    WAREHOUSE: "GALPAO",
    LAND: "TERRENO",
  }[propertyType] || propertyType.replace(/[^A-Z0-9]/gi, "").slice(0, 6);
  return {
    ticker: "RE-" + propertyCode + "-" + cep,
    name: propertyType + " · " + city,
    property_type: propertyType,
    description: value("#property-address") || propertyType + " em " + city,
    country: value("#property-country"),
    state: value("#property-state"),
    city,
    cep,
    acquisition_date: value("#property-acquisition-date"),
    acquisition_value: moneyValue(value("#property-acquisition-value")),
    ownership_percentage: value("#property-ownership"),
    current_manual_value: moneyValue(value("#property-value")),
    valuation_date: document.querySelector("#effective-date")?.value || "",
  };
}

function moneyValue(value) {
  const normalized = String(value || "").trim().replace(/[R$\s]/g, "");
  if (!normalized) return "";
  if (normalized.includes(",")) return normalized.replace(/\./g, "").replace(",", ".");
  return normalized;
}

function bindMoneyFormatting(scope) {
  scope?.querySelectorAll("[data-money]").forEach(input => {
    input.addEventListener("blur", () => {
      const numeric = Number(moneyValue(input.value));
      if (Number.isFinite(numeric)) {
        input.value = numeric.toLocaleString("pt-BR", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
      }
    });
  });
}

function fixedIncomeLotTicker(name) {
  const normalizedName = name.toUpperCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^A-Z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 18) || "APLICACAO";
  const suffix = globalThis.crypto?.randomUUID?.().replace(/-/g, "").slice(0, 8)
    || `${Date.now()}${Math.random()}`.replace(/\D/g, "").slice(-8);
  return `FI-${normalizedName}-${suffix}`;
}

function setFixedIncomeFields() {
  const scope = document.querySelector("#fixed-income-details");
  if (!scope) return;
  const instrument = scope.querySelector("#fi-instrument");
  const indexer = scope.querySelector("#fi-indexer");
  const fields = {
    rate: scope.querySelector("#fi-rate"),
    percentage: scope.querySelector("#fi-percentage"),
    spread: scope.querySelector("#fi-spread"),
  };
  const indexerLabel = indexer.closest("label");
  const savingsRule = scope.querySelector("#fi-savings-rule");
  const instrumentHint = scope.querySelector("#fi-instrument-hint");
  const savings = instrument.value === "SAVINGS_ACCOUNT";
  if (savings) {
    indexer.value = "SAVINGS_RULE";
    indexer.disabled = true;
  } else {
    indexer.disabled = false;
    if (indexer.value === "SAVINGS_RULE") indexer.value = "";
  }
  indexerLabel.hidden = false;
  savingsRule.hidden = !savings;
  if (instrumentHint) {
    instrumentHint.textContent = instrument.value === "RDB"
      ? "RDB: remuneração segue as mesmas regras do CDB e pode ser emitido por financeiras e fintechs."
      : instrument.value === "CDB"
        ? "CDB: título de renda fixa emitido por instituição bancária."
        : "";
    instrumentHint.hidden = !["CDB", "RDB"].includes(instrument.value);
  }
  const visible = {
    rate: !savings && indexer.value === "PREFIXED",
    percentage: !savings && ["CDI_PERCENT", "CDI_PLUS"].includes(indexer.value),
    spread: !savings && ["CDI_PLUS", "IPCA_PLUS"].includes(indexer.value),
  };
  Object.entries(fields).forEach(([name, input]) => {
    input.closest("label").hidden = !visible[name];
    input.required = visible[name];
    input.disabled = !visible[name];
    if (!visible[name]) input.value = "";
  });
}

function setPensionFields() {
  const details = document.querySelector("#pension-details");
  if (!details || details.hidden) return;
  const system = details.querySelector("#pension-system")?.value;
  const origin = details.querySelector("#pension-origin")?.value;
  const match = details.querySelector("#pension-match-enabled")?.value === "true";
  const vesting = details.querySelector("#pension-vesting-enabled")?.value === "true";
  const composition = details.querySelector("#pension-composition")?.checked;
  const open = details.querySelector("#pension-open-fields");
  const closed = details.querySelector("#pension-closed-fields");
  const employer = details.querySelector("#pension-employer-fields");
  const matchFields = details.querySelector("#pension-match-fields");
  const vestingFields = details.querySelector("#pension-vesting-fields");
  const compositionFields = details.querySelector("#pension-composition-fields");
  if (open) open.hidden = system !== "OPEN";
  if (closed) closed.hidden = system !== "CLOSED";
  if (employer) employer.hidden = !["EMPLOYER", "ASSOCIATION"].includes(origin);
  const employerOnly = [
    details.querySelector("#pension-match-enabled")?.closest("label"),
    details.querySelector("#pension-match-fields"),
    details.querySelector("#pension-vesting-enabled")?.closest("label"),
    details.querySelector("#pension-vesting-fields"),
  ];
  employerOnly.forEach(item => { if (item) item.hidden = origin !== "EMPLOYER"; });
  const sponsorHeading = employer?.querySelector("h4");
  if (sponsorHeading) sponsorHeading.textContent = origin === "ASSOCIATION" ? "Associação ou entidade instituidora" : "Previdência empresarial";
  if (matchFields) matchFields.hidden = !match || origin !== "EMPLOYER";
  if (vestingFields) vestingFields.hidden = !vesting || origin !== "EMPLOYER";
  if (compositionFields) compositionFields.hidden = !composition;
  details.querySelectorAll("input, select").forEach(input => {
    const hidden = input.closest("[hidden]") !== null;
    input.disabled = hidden;
    if (hidden) {
      input.required = false;
    }
  });
}

function currencyForCountry(value) {
  const country = value.trim().toUpperCase();
  const currencies = {
    BR: "BRL", BRASIL: "BRL",
    US: "USD", USA: "USD", EUA: "USD", "ESTADOS UNIDOS": "USD",
    CA: "CAD", CANADA: "CAD", "CANADÁ": "CAD",
    GB: "GBP", UK: "GBP", "REINO UNIDO": "GBP",
    DE: "EUR", FR: "EUR", ES: "EUR", IT: "EUR", PT: "EUR",
    JP: "JPY", JAPAO: "JPY", "JAPÃO": "JPY",
    CH: "CHF", SUICA: "CHF", "SUÍÇA": "CHF",
    AU: "AUD", AUSTRALIA: "AUD", "AUSTRÁLIA": "AUD",
  };
  return currencies[country] || null;
}

function arrangeOperationForm() {
  const form = document.querySelector("#trade-form");
  const grid = document.querySelector("#operation-form-grid");
  const advanced = document.querySelector("#operation-more-content");
  if (!form || !grid || !advanced || form.dataset.arranged) return;
  form.dataset.arranged = "true";
  const typeSelect = document.querySelector("#event_type");
  const oldTypeLabel = form.querySelector('label[for="event_type"]');
  const typeLabel = document.createElement("label");
  typeLabel.textContent = "Tipo de lançamento";
  typeLabel.append(typeSelect);
  oldTypeLabel?.remove();
  advanced.append(typeLabel);

  const moveField = (id, destination) => {
    const input = form.querySelector(`#${id}`);
    if (!input) return;
    const label = form.querySelector(`label[for="${id}"]`);
    const wrapper = document.createElement("div");
    wrapper.className = "operation-field";
    if (label) wrapper.append(label);
    wrapper.append(input);
    destination.append(wrapper);
  };
  const wrapExistingField = (id, parent, destination) => {
    const input = form.querySelector("#" + id);
    if (!input) return;
    const label = form.querySelector('label[for="' + id + '"]');
    const wrapper = document.createElement("div");
    wrapper.className = "operation-field";
    if (parent?.id) wrapper.id = parent.id;
    if (label) wrapper.append(label);
    wrapper.append(input);
    if (parent) parent.replaceWith(wrapper);
    destination.append(wrapper);
  };
  wrapExistingField("trade-asset-class", form.querySelector("#asset-class-details"), grid);
  wrapExistingField("ticker", form.querySelector("#asset-details"), grid);
  const dateInput = form.querySelector("#effective-date");
  if (dateInput) {
    const dateLabel = form.querySelector('label[for="effective-date"]');
    const wrapper = document.createElement("div");
    wrapper.className = "operation-field";
    if (dateLabel) wrapper.append(dateLabel);
    wrapper.append(dateInput);
    grid.append(wrapper);
  }
  const tradeDetails = form.querySelector("#trade-details");
  if (tradeDetails) {
    moveField("quantity", tradeDetails);
    moveField("unit_price", tradeDetails);
    grid.append(tradeDetails);
  }
  ["#dividend-details", "#jcp-details", "#external-flow-details"].forEach(selector => {
    const node = form.querySelector(selector);
    if (node) grid.append(node);
  });
  ["country", "currency-code", "sector"].forEach(id => moveField(id, advanced));
  ["#capital-flow-details", "#fixed-income-details", "#pension-details", "#real-estate-details"].forEach(selector => {
    const node = form.querySelector(selector);
    if (node) advanced.append(node);
  });
  const country = document.querySelector("#country");
  if (country) country.value ||= "BR";
  const currency = document.querySelector("#currency-code");
  if (currency) currency.value ||= "BRL";
}

export function openOperationModal(options = {}) {
  const dialog = document.querySelector("#operation-modal");
  if (!dialog) return;
  const { eventType = "BUY", assetClass, ticker, name, country, currencyCode, sector } = options || {};
  const type = document.querySelector("#event_type");
  const classSelect = document.querySelector("#trade-asset-class");
  const symbol = document.querySelector("#ticker");
  if (assetClass && classSelect && Array.from(classSelect.options).some(option => option.value === assetClass)) {
    classSelect.value = assetClass;
  }
  if (type && Array.from(type.options).some(option => option.value === eventType)) type.value = eventType;
  if (symbol && ticker) {
    symbol.value = ticker;
    symbol.dataset.assetName = name || "";
  }
  if (country) document.querySelector("#country").value = country;
  if (currencyCode) document.querySelector("#currency-code").value = currencyCode;
  if (sector) document.querySelector("#sector").value = sector;
  setOperationFields(type?.value || "BUY");
  symbol?.loadFixedIncomeSaleOptions?.();
  document.querySelector("#operation-more-options").open = !["BUY", "SELL"].includes(type?.value)
    || ["FIXED_INCOME", "PENSION", "REAL_ESTATE"].includes(classSelect?.value);
  syncQuickOperationButtons();
  updateOperationSummary();
  const message = document.querySelector("#message");
  if (message) { message.textContent = ""; message.className = "message"; }
  const dateInput = document.querySelector("#effective-date");
  if (dateInput && !dateInput.value) {
    const now = new Date();
    dateInput.value = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0,10);
  }
  if (!dialog.open) dialog.showModal();
  requestAnimationFrame(() => {
    const target = symbol && !symbol.hidden && !symbol.closest("[hidden]") ? symbol : dialog.querySelector("input:not([type=hidden]):not([disabled]), select:not([disabled])");
    target?.focus();
  });
}

function bindOperationModal() {
  const dialog = document.querySelector("#operation-modal");
  document.querySelector("#header-new-operation")?.addEventListener("click", () => openOperationModal());
  document.querySelector("#operations-new-operation")?.addEventListener("click", () => openOperationModal());
  window.addEventListener("income:open-operation", event => openOperationModal(event.detail));
  dialog?.querySelectorAll("[data-close-operation], #cancel-operation").forEach(button => button.addEventListener("click", () => dialog.close()));
  dialog?.querySelectorAll("[data-quick-operation]").forEach(button => button.addEventListener("click", () => {
    const type = button.dataset.quickOperation;
    document.querySelector("#event_type").value = type;
    setOperationFields(type);
    document.querySelector("#ticker").loadFixedIncomeSaleOptions?.();
    syncQuickOperationButtons();
    updateOperationSummary();
  }));
  const recurrence = document.querySelector("#recurrence-modal");
  document.querySelector("#new-recurring-button")?.addEventListener("click", () => {
    if (!recurrence.open) recurrence.showModal();
    requestAnimationFrame(() => recurrence.querySelector("input:not([disabled]), select:not([disabled])")?.focus());
  });
  recurrence?.querySelectorAll("[data-close-recurrence]").forEach(button => button.addEventListener("click", () => recurrence.close()));
  const importDialog = document.querySelector("#operations-import-modal");
  document.querySelectorAll("[data-open-import]").forEach(button => button.addEventListener("click", () => {
    const source = button.dataset.openImport;
    document.querySelectorAll("[data-import-source]").forEach(panel => { panel.hidden = panel.dataset.importSource !== source; });
    const title = document.querySelector("#operations-import-title");
    if (title) title.textContent = source === "b3" ? "Importar da B3" : "Importar arquivo IRPF";
    if (!importDialog.open) importDialog.showModal();
  }));
  importDialog?.querySelectorAll("[data-close-import]").forEach(button => button.addEventListener("click", () => importDialog.close()));
  const historyDialog = document.querySelector("#operations-import-history-modal");
  document.querySelectorAll("[data-open-import-history]").forEach(button => button.addEventListener("click", () => {
    if (!historyDialog.open) historyDialog.showModal();
    loadB3ImportHistory(true);
  }));
  historyDialog?.querySelectorAll("[data-close-import-history]").forEach(button => button.addEventListener("click", () => historyDialog.close()));
  const tabs = Array.from(document.querySelectorAll("[data-operations-tab]"));
  syncOperationsTabs("ALL");
  tabs.forEach(button => {
    button.addEventListener("click", () => selectOperationsTab(button.dataset.operationsTab));
    button.addEventListener("keydown", event => {
      const current = tabs.indexOf(button);
      const next = event.key === "ArrowRight" ? (current + 1) % tabs.length
        : event.key === "ArrowLeft" ? (current - 1 + tabs.length) % tabs.length
          : event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : current;
      if (next === current) return;
      event.preventDefault();
      tabs[next].focus();
      selectOperationsTab(tabs[next].dataset.operationsTab);
    });
  });
}

function syncQuickOperationButtons() {
  const value = document.querySelector("#event_type")?.value;
  document.querySelectorAll("[data-quick-operation]").forEach(button => {
    const selected = button.dataset.quickOperation === value;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
}

function updateOperationSummary() {
  const output = document.querySelector("#operation-estimated-total");
  if (!output) return;
  const type = document.querySelector("#event_type")?.value;
  const assetClass = document.querySelector("#trade-asset-class")?.value;
  const fixedIncomeSale = type === "SELL" && assetClass === "FIXED_INCOME";
  const number = selector => {
    const input = document.querySelector(selector);
    if (!input || !input.value.trim()) return null;
    const result = Number(moneyValue(input.value));
    return Number.isFinite(result) ? result : null;
  };
  const quantity = number("#quantity");
  const price = number("#unit_price");
  const currency = document.querySelector("#currency-code")?.value || "BRL";
  let amount = null;
  let label = type === "SELL" ? "Valor bruto da venda" : "Valor estimado";
  if (fixedIncomeSale) {
    amount = number("#fixed-income-sale-value");
    label = "Valor total da venda";
  } else if (["BUY", "SELL"].includes(type) && !["FIXED_INCOME", "PENSION", "REAL_ESTATE"].includes(assetClass)) {
    if (quantity > 0 && price > 0) amount = quantity * price;
  } else if (type === "BUY" && assetClass === "FIXED_INCOME") {
    amount = number("#fi-principal");
  } else if (type === "BUY" && assetClass === "PENSION") {
    amount = number("#pension-balance");
  } else if (type === "BUY" && assetClass === "REAL_ESTATE") {
    amount = number("#property-value");
  } else if (type === "DIVIDEND" || type === "DEPOSIT" || type === "WITHDRAWAL") {
    amount = number(type === "DIVIDEND" ? "#dividend-amount" : "#external-flow-amount");
    label = type === "DIVIDEND" ? "Valor recebido" : "Valor do fluxo";
  } else if (type === "INTEREST_ON_EQUITY") {
    const gross = number("#jcp-gross"), tax = number("#jcp-tax");
    amount = gross !== null && tax !== null ? gross - tax : null;
    label = "Valor líquido do JCP";
  }
  output.textContent = amount === null ? "Preencha os campos obrigatórios" : money(amount, currency);
  document.querySelector("#operation-summary-label").textContent = label;
  document.querySelector("#operation-summary-note").textContent = amount === null
    ? "O total aparece quando os campos obrigatórios forem preenchidos."
    : "Resumo calculado com os dados informados. Custos por operação não fazem parte do modelo atual.";
}

function bindOperationSearch() {
  const ticker = document.querySelector("#ticker");
  if (!ticker || ticker.dataset.searchBound) return;
  ticker.dataset.searchBound = "true";
  const listId = "asset-search-options";
  const list = document.createElement("datalist");
  list.id = listId;
  document.body.append(list);
  ticker.setAttribute("list", listId);
  let timer;
  let requestId = 0;
  let candidatesBySymbol = new Map();
  const fixedIncomeSaleSelected = () => document.querySelector("#event_type")?.value === "SELL"
    && document.querySelector("#trade-asset-class")?.value === "FIXED_INCOME";
  const loadFixedIncomeSaleOptions = async () => {
    if (!fixedIncomeSaleSelected()) return;
    const current = ++requestId;
    try {
      const holdings = await portfolioApi.holdings();
      if (current !== requestId || !fixedIncomeSaleSelected()) return;
      const assets = (holdings.classes || [])
        .filter(group => group.asset_class === "FIXED_INCOME")
        .flatMap(group => group.assets || []);
      candidatesBySymbol = new Map(assets.map(asset => [String(asset.ticker).toUpperCase(), asset]));
      list.innerHTML = assets.map(asset => `<option value="${escapeAttribute(asset.ticker)}" label="${escapeAttribute(asset.contract_label || asset.name || asset.ticker)}">${escapeAttribute(asset.contract_label || asset.name || asset.ticker)}</option>`).join("");
    } catch { list.replaceChildren(); }
  };
  ticker.loadFixedIncomeSaleOptions = loadFixedIncomeSaleOptions;
  ticker.addEventListener("input", () => {
    ticker.dataset.assetName = "";
    clearTimeout(timer);
    const query = ticker.value.trim();
    if (fixedIncomeSaleSelected()) {
      ticker.setCustomValidity("");
      const candidate = candidatesBySymbol.get(query.toUpperCase());
      ticker.dataset.assetName = candidate?.name || "";
      updateOperationSummary();
      return;
    }
    if (query.length < 2) { list.replaceChildren(); return; }
    timer = setTimeout(async () => {
      const current = ++requestId;
      try {
        const assetClass = document.querySelector("#trade-asset-class").value;
        const response = await portfolioApi.assetSearch(query, assetClass);
        if (current !== requestId) return;
        candidatesBySymbol = new Map((response.candidates || []).map(candidate => [candidate.symbol.toUpperCase(), candidate]));
        list.innerHTML = [...candidatesBySymbol.values()].map(candidate => `<option value="${escapeAttribute(candidate.symbol)}">${escapeAttribute(candidate.name)}</option>`).join("");
      } catch { list.replaceChildren(); }
    }, 300);
  });
  ticker.addEventListener("change", () => {
    const candidate = candidatesBySymbol.get(ticker.value.trim().toUpperCase());
    if (fixedIncomeSaleSelected()) {
      if (!candidate) ticker.setCustomValidity("Selecione uma posição aberta de Renda Fixa da carteira.");
      else {
        ticker.setCustomValidity("");
        ticker.dataset.assetName = candidate.name || candidate.contract_label || "";
      }
      updateOperationSummary();
      return;
    }
    if (!candidate) return;
    ticker.value = candidate.symbol;
    ticker.dataset.assetName = candidate.name || "";
    const classSelect = document.querySelector("#trade-asset-class");
    if (candidate.suggested_asset_class && Array.from(classSelect.options).some(option => option.value === candidate.suggested_asset_class)) {
      classSelect.value = candidate.suggested_asset_class;
      setOperationFields(document.querySelector("#event_type").value);
    }
    if (candidate.country) document.querySelector("#country").value = candidate.country;
    if (candidate.currency_code) document.querySelector("#currency-code").value = candidate.currency_code;
    if (candidate.sector) document.querySelector("#sector").value = candidate.sector;
    updateOperationSummary();
  });
}

const escapeAttribute = value => String(value ?? "").replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));

export function bindOperations() {
  const form = document.querySelector("#trade-form");
  if (!form || operationsBound) return;
  operationsBound = true;
  document.querySelector("#event_type")?.insertAdjacentHTML(
    "afterbegin", '<option value="INTEREST_ON_EQUITY">JCP</option>',
  );
  document.querySelector("#dividend-details")?.insertAdjacentHTML(
    "afterend", '<div id="jcp-details" hidden><label for="jcp-gross">JCP bruto<input id="jcp-gross" type="number" min="0.01" step="0.01"></label><label for="jcp-tax">IR retido<input id="jcp-tax" type="number" min="0" step="0.01" value="0"></label><p class="field-help">O valor líquido será creditado automaticamente.</p></div>',
  );
  document.querySelector("[data-import-source=\"irpf\"]")?.insertAdjacentHTML("beforeend", '<section class="card" id="irpf-import-card"><h2>Importar IRPF</h2><p>Piloto: importa somente ações brasileiras da posição em 31/12/2025 como compras consolidadas nessa data.</p><label for="irpf-workbook">Relatório IRPF (.xlsx)<input id="irpf-workbook" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"></label><button id="irpf-preview" type="button" disabled>Gerar prévia</button><div id="irpf-preview-result" class="empty">Selecione a planilha para conferir as posições.</div><button id="irpf-confirm" type="button" hidden>Confirmar importação</button><div class="message" id="irpf-import-message" role="alert"></div></section>');
  document.querySelector("[data-import-source=\"b3\"]")?.insertAdjacentHTML("beforeend", '<section class="card" id="b3-import-card"><h2>Importar relatório B3</h2><p>Gere uma prévia auditável antes de aplicar. Linhas pendentes de revisão não são lançadas.</p><label for="b3-workbook">Relatório B3 (.xlsx)<input id="b3-workbook" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"></label><button id="b3-preview" type="button" disabled>Gerar prévia B3</button><div id="b3-preview-result" class="empty">Selecione um relatório B3.</div><button id="b3-apply" type="button" disabled>Aplicar lançamentos</button><div class="message" id="b3-import-message" role="alert"></div></section>');
  let b3WorkbookBase64 = "", b3FileName = "", b3Preview = null;
  const b3File = document.querySelector("#b3-workbook"), b3PreviewButton = document.querySelector("#b3-preview");
  const b3ApplyButton = document.querySelector("#b3-apply"), b3Result = document.querySelector("#b3-preview-result"), b3Message = document.querySelector("#b3-import-message");
  b3File?.addEventListener("change", async () => {
    const [file] = b3File.files || []; b3WorkbookBase64 = ""; b3Preview = null; b3ApplyButton.disabled = true; b3PreviewButton.disabled = !file;
    if (!file) return;
    b3FileName = file.name;
    const reader = new FileReader();
    reader.onload = () => { b3WorkbookBase64 = String(reader.result).split(",", 2)[1] || ""; };
    reader.readAsDataURL(file);
  });
  b3PreviewButton?.addEventListener("click", async () => {
    try { await withProcessing(b3PreviewButton, async () => {
      const preview = await portfolioApi.previewB3Import({ workbook_base64: b3WorkbookBase64, file_name: b3FileName });
      b3Preview = preview;
      const counts = preview.counts;
      const items = preview.items;
      const by = predicate => items.filter(predicate);
      const groups = [
        ["review", "⚠ Requerem revisão", by(x => x.status === "REVIEW_REQUIRED")],
        ["ready", "✓ Prontos para aplicar", by(x => x.status === "NEW")],
        ["custody", "↔ Transferências de custódia", by(x => x.reason_code === "CUSTODY_TRANSFER")],
        ["loan", "↔ Empréstimos de ativos", by(x => x.reason_code === "STOCK_LOAN")],
        ["unsupported", "⊘ Não suportados", by(x => x.status === "UNSUPPORTED" && !["CUSTODY_TRANSFER", "STOCK_LOAN"].includes(x.reason_code))],
        ["duplicate", "= Duplicados", by(x => x.status === "DUPLICATE")],
        ["invalid", "! Inválidos", by(x => x.status === "INVALID")],
      ];
      const totalClassified = counts.new + counts.review_required + counts.unsupported + counts.duplicate + counts.invalid;
      const renderRows = rows => table(["Linha", "Ativo", "Data", "Movimentação", "Status", "Motivo"], rows.slice(0, 50).map(x => `<tr><td>${x.source_row}</td><td>${x.normalized_symbol || x.source_symbol || "—"}</td><td>${x.event_date || "—"}</td><td>${x.original_movement || "—"}</td><td>${x.status}</td><td>${x.reason_code || "—"}</td></tr>`)) + (rows.length > 50 ? `<p>Exibindo 50 de ${rows.length} registros.</p>` : "");
      b3Result.innerHTML = `<h3>Prévia da importação B3</h3><div class="b3-summary">Total: ${counts.total} · Prontos: ${counts.new} · Revisão: ${counts.review_required} · Ignorados: ${counts.unsupported} · Duplicados: ${counts.duplicate} · Inválidos: ${counts.invalid}</div>${groups.map(([key,label,rows]) => `<section class="b3-group"><button type="button" class="secondary b3-toggle" data-b3-group="${key}">${label} <strong>${rows.length}</strong> <span>Ver</span></button><div class="b3-group-body" id="b3-group-${key}" hidden></div></section>`).join("")}<p class="b3-consistency">Total classificado: ${totalClassified}${totalClassified === counts.total ? "" : " — erro interno de consistência"}</p>`;
      groups.forEach(([key, , rows]) => document.querySelector(`#b3-group-${key}`)?.previousElementSibling?.addEventListener("click", event => { const body = event.currentTarget.nextElementSibling; const opening = body.hidden; body.hidden = !opening; event.currentTarget.querySelector("span").textContent = opening ? "Fechar" : "Ver"; if (opening && !body.dataset.rendered) { if (key === "ready") { const types = [["Compra", "BUY"], ["Venda", "SELL"], ["Dividendos", "DIVIDEND"], ["JCP", "JCP"], ["Rendimentos", "INCOME"]]; body.innerHTML = types.map(([label,type]) => { const subset=rows.filter(x => (x.event_type || x.income_type) === type); return `<details><summary>${label} — ${subset.length}</summary>${renderRows(subset)}</details>`; }).join(""); } else if (key === "review") { const reasons={}; rows.forEach(x => { const reason=x.reason_code || "Outro"; (reasons[reason] ||= []).push(x); }); body.innerHTML=Object.entries(reasons).map(([reason,subset]) => `<details><summary>${reason} — ${subset.length}</summary>${renderRows(subset)}</details>`).join(""); } else body.innerHTML=renderRows(rows); body.dataset.rendered="true"; } }));
      b3ApplyButton.disabled = counts.new === 0;
      b3ApplyButton.textContent = `Aplicar ${counts.new} lançamentos`;
      if (counts.new) setMessage(b3Message, "Você pode aplicar os lançamentos prontos; os itens listados serão ignorados.", "success");
      else setMessage(b3Message, "Não há lançamentos novos para aplicar.", "error");
    }); } catch (error) { setMessage(b3Message, friendlyError(error), "error"); }
  });
  b3ApplyButton?.addEventListener("click", async () => {
    try { await withProcessing(b3ApplyButton, async () => {
      const result = await portfolioApi.applyB3Import(b3Preview.batch_id);
      setMessage(b3Message, `${result.applied_count} lançamento(s) B3 aplicado(s).`, "success"); b3ApplyButton.disabled = true;
      await Promise.all([loadPortfolio(), loadOperations({ reset: true })]);
    }); } catch (error) { setMessage(b3Message, friendlyError(error), "error"); }
  });
  let irpfWorkbookBase64 = "";
  const irpfFile = document.querySelector("#irpf-workbook");
  const irpfPreviewButton = document.querySelector("#irpf-preview");
  const irpfConfirmButton = document.querySelector("#irpf-confirm");
  const irpfPreview = document.querySelector("#irpf-preview-result");
  const irpfMessage = document.querySelector("#irpf-import-message");
  irpfFile?.addEventListener("change", async () => {
    const [file] = irpfFile.files || [];
    irpfWorkbookBase64 = "";
    irpfConfirmButton.hidden = true;
    irpfPreviewButton.disabled = !file;
    irpfPreview.textContent = file ? "Pronto para gerar a prévia." : "Selecione a planilha para conferir as posições.";
    if (!file) return;
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error("Não foi possível ler a planilha."));
      reader.readAsDataURL(file);
    });
    irpfWorkbookBase64 = String(dataUrl).split(",", 2)[1] || "";
  });
  irpfPreviewButton?.addEventListener("click", async () => {
    try {
      await withProcessing(irpfPreviewButton, async () => {
        const preview = await portfolioApi.previewIrpfBrazilianStocks(irpfWorkbookBase64);
        irpfPreview.innerHTML = table(
          ["Ativo", "Quantidade", "Custo médio", "Custo total"],
          preview.items.map(item => `<tr><td>${item.ticker}</td><td>${item.quantity}</td><td>${money(item.unit_price)}</td><td>${money(item.total_cost)}</td></tr>`),
        ) + `<p><strong>${preview.items.length} ações brasileiras</strong> em 31/12/2025. Custo total: <strong>${money(preview.total_cost)}</strong>.</p>`;
        irpfConfirmButton.hidden = false;
        setMessage(irpfMessage, "Confira a prévia antes de confirmar a carga.", "success");
      });
    } catch (error) {
      setMessage(irpfMessage, friendlyError(error), "error");
    }
  });
  irpfConfirmButton?.addEventListener("click", async () => {
    if (!window.confirm("Importar as ações brasileiras mostradas na prévia? A operação cria compras em 31/12/2025.")) return;
    try {
      await withProcessing(irpfConfirmButton, async () => {
        const result = await portfolioApi.importIrpfBrazilianStocks(irpfWorkbookBase64);
        setMessage(irpfMessage, `${result.imported} ações brasileiras importadas com sucesso.`, "success");
        irpfConfirmButton.hidden = true;
        await Promise.all([loadPortfolio(), loadOperations({ reset: true })]);
      });
    } catch (error) {
      setMessage(irpfMessage, friendlyError(error), "error");
    }
  });
  const typeInput = document.querySelector("#event_type");
  document.querySelector("#trade-asset-class")?.insertAdjacentHTML(
    "beforeend",
    '<option value="PENSION">Previdência</option><option value="REAL_ESTATE">Imóveis</option>',
  );
  document.querySelector("#asset-class-details")?.insertAdjacentHTML(
    "afterend",
    '<div id="capital-flow-details"><label for="capital-flow-type">Origem do recurso</label><select id="capital-flow-type"><option value="UNKNOWN">Não informado</option><option value="EXTERNAL_CAPITAL">Capital externo</option><option value="INTERNAL_TRANSFER">Transferência interna</option><option value="EMPLOYER_CONTRIBUTION">Contribuição da empresa</option></select><label id="capital-flow-source-label" hidden for="capital-flow-source">Classe de origem</label><select id="capital-flow-source" hidden><option value="">Selecione</option><option value="BRAZILIAN_STOCK">Ações Brasil</option><option value="BRAZILIAN_ETF">ETF Brasil</option><option value="FII">FIIs</option><option value="FIXED_INCOME">Renda fixa</option><option value="PENSION">Previdência</option><option value="REAL_ESTATE">Imóveis</option><option value="INTERNATIONAL">Exterior</option><option value="INTERNATIONAL_ETF">ETF internacional</option><option value="US_REIT">REITs EUA</option><option value="CRYPTO">Cripto</option><option value="OTHER">Outros</option></select></div>',
  );
  const updateCapitalFlowFields = () => {
    const internal = document.querySelector("#capital-flow-type")?.value === "INTERNAL_TRANSFER";
    ["#capital-flow-source", "#capital-flow-source-label"].forEach(selector => {
      const element = document.querySelector(selector);
      if (element) element.hidden = !internal;
    });
    const source = document.querySelector("#capital-flow-source");
    if (source) source.required = internal;
  };
  document.querySelector("#capital-flow-type")?.addEventListener("change", updateCapitalFlowFields);
  updateCapitalFlowFields();
  document.querySelector("#external-flow-details")?.insertAdjacentHTML("afterend", '<div id="fixed-income-details" hidden><label>Nome do investimento<input id="wealth-name" required></label><label>Instrumento<select id="fi-instrument"><option>CDB</option><option>LCI</option><option>LCA</option><option>TESOURO_DIRETO</option><option value="SAVINGS_ACCOUNT">Poupança</option></select></label><label>Indexador<select id="fi-indexer" required><option value="" selected disabled>Selecione o indexador</option><option value="PREFIXED">Prefixado</option><option value="CDI_PERCENT">% do CDI</option><option value="CDI_PLUS">% do CDI + spread</option><option value="IPCA_PLUS">IPCA + spread</option><option value="SAVINGS_RULE" hidden>Regra da poupança</option></select></label><label>Principal<input id="fi-principal" type="number" min="0.01" step="0.01" required></label><label>Taxa anual (%)<input id="fi-rate" type="number" step="0.01"></label><label>% do CDI<input id="fi-percentage" type="number" min="0.01" step="0.01"></label><label>Spread anual (%)<input id="fi-spread" type="number" step="0.01"></label></div><div id="pension-details" hidden><label>Identificador<input id="wealth-ticker" maxlength="32" required></label><label>Nome<input id="wealth-name" required></label><label>Instituição<input id="pension-institution" required></label><label>Plano<input id="pension-name" required></label><label>Saldo informado<input id="pension-balance" type="number" min="0" step="0.01" required></label><label>Tipo<select id="pension-type"><option>PGBL</option><option>VGBL</option></select></label><label>Regime<select id="pension-tax"><option>PROGRESSIVO</option><option>REGRESSIVO</option></select></label></div><div id="real-estate-details" hidden><label>Tipo<input id="property-type" value="APARTAMENTO" required></label><label>CEP<input id="property-cep" required></label><label>Valor atual<input id="property-value" type="text" inputmode="decimal" data-money required></label></div>');
  const fixedIncomeDetails = document.querySelector("#fixed-income-details");
  document.querySelector("#fi-instrument")?.insertAdjacentHTML(
    "afterbegin",
    '<option value="RDB">RDB</option>',
  );
  if (document.querySelector("#fi-instrument")) {
    document.querySelector("#fi-instrument").value = "CDB";
  }
  document.querySelector("#fi-instrument")?.insertAdjacentHTML(
    "afterend",
    '<p id="fi-instrument-hint" class="fixed-income-rule" hidden></p>',
  );
  document.querySelector("#pension-institution")?.insertAdjacentHTML("afterend", '<label>CNPJ da instituição<input id="pension-cnpj" inputmode="numeric" required></label>');
  const pensionDetails = document.querySelector("#pension-details");
  if (pensionDetails) {
    pensionDetails.outerHTML = '<div id="pension-details" hidden><h3>Nova Previdência</h3><label>Como você possui esta previdência?<select id="pension-origin"><option value="PARTICULAR">Particular</option><option value="EMPLOYER">Pela empresa</option><option value="ASSOCIATION">Por associação ou entidade</option></select></label><label>Estrutura<select id="pension-system"><option value="OPEN">Aberta</option><option value="CLOSED">Fechada</option><option value="UNKNOWN">Não sei</option></select></label><label>Nome do plano<input id="pension-name" required></label><label>Instituição administradora<input id="pension-institution" required></label><label>CNPJ da instituição (opcional)<input id="pension-cnpj" inputmode="numeric"></label><div id="pension-open-fields"><label>Produto<select id="pension-product"><option value="PGBL">PGBL</option><option value="VGBL">VGBL</option><option value="OTHER">Outro</option><option value="UNKNOWN">Não sei</option></select></label><label>Número do processo SUSEP (opcional)<input id="pension-susep"></label></div><div id="pension-closed-fields" hidden><label>Modalidade<select id="pension-modality"><option value="CD">CD — Contribuição Definida</option><option value="CV">CV — Contribuição Variável</option><option value="BD">BD — Benefício Definido</option><option value="UNKNOWN">Não sei</option></select></label><label>CNPB (opcional)<input id="pension-cnpb"></label></div><label>Regime tributário<select id="pension-tax"><option value="UNDEFINED">Ainda não definido</option><option value="PROGRESSIVE">Progressivo</option><option value="REGRESSIVE">Regressivo</option></select></label><label>Saldo atual<input id="pension-balance" type="number" min="0" step="0.01" required></label><label>Data do saldo<input id="pension-balance-date" type="date" required></label><label><input id="pension-composition" type="checkbox"> Quero informar a composição do saldo</label><div id="pension-composition-fields" hidden><label>Saldo do participante<input id="pension-participant-balance" type="number" min="0" step="0.01"></label><label>Saldo da empresa/patrocinador<input id="pension-sponsor-balance" type="number" min="0" step="0.01"></label></div><div id="pension-employer-fields" hidden><h4>Previdência empresarial</h4><label>Empresa patrocinadora<input id="pension-sponsor-name"></label><label>CNPJ da empresa patrocinadora (opcional)<input id="pension-sponsor-cnpj" inputmode="numeric"></label><label>A empresa faz contrapartida?<select id="pension-match-enabled"><option value="">Não sei</option><option value="true">Sim</option><option value="false">Não</option></select></label><div id="pension-match-fields" hidden><label>Percentual da contrapartida<input id="pension-match-rate" type="number" min="0" step="0.01"></label><label>Limite da contrapartida (opcional)<input id="pension-match-limit" type="number" min="0" step="0.01"></label><label>Regra da contrapartida (opcional)<input id="pension-match-notes"></label></div><label>Existe regra de aquisição (vesting)?<select id="pension-vesting-enabled"><option value="">Não sei</option><option value="true">Sim</option><option value="false">Não</option></select></label><div id="pension-vesting-fields" hidden><label>Percentual adquirido atualmente<input id="pension-vested-percentage" type="number" min="0" max="100" step="0.01"></label><label>Regra/observação (opcional)<input id="pension-vesting-notes"></label></div></div></div>';
  }
  document.querySelector("#pension-open-fields")?.insertAdjacentHTML("beforeend", '<p class="field-help">Opcional: informe o fundo onde os recursos estão aplicados para acompanhar a <strong>rentabilidade do fundo</strong>, não a sua rentabilidade individual.</p><label>Nome do fundo / FIE (opcional)<input id="pension-vehicle-name"></label><label>CNPJ do fundo / FIE (opcional)<input id="pension-vehicle-cnpj" inputmode="numeric" maxlength="18"><small>Use o CNPJ do fundo, não o CNPJ da administradora.</small></label>');
  const realEstate = document.querySelector("#real-estate-details");
  const propertyTypeInput = realEstate?.querySelector("#property-type");
  if (propertyTypeInput) propertyTypeInput.outerHTML = '<select id="property-type" required><option value="APARTMENT">Apartamento</option><option value="HOUSE">Casa</option><option value="WAREHOUSE">Galpão</option><option value="LAND">Terreno</option></select>';
  realEstate?.querySelector("#property-cep")?.closest("label").insertAdjacentHTML("afterend", '<label>País<input id="property-country" value="BR" required></label><label>Moeda<input id="property-currency" value="BRL" readonly></label><label>Estado<input id="property-state" required></label><label>Cidade<input id="property-city" required></label><label>Endereço<input id="property-address" readonly></label><label>Data de aquisição<input id="property-acquisition-date" type="date" required></label><label>Valor de aquisição<input id="property-acquisition-value" type="text" inputmode="decimal" data-money required></label><label>Participação (%)<input id="property-ownership" type="number" min="0.01" max="100" step="0.01" value="100" required></label>');
  bindMoneyFormatting(realEstate);
  const propertyCep = realEstate?.querySelector("#property-cep");
  propertyCep?.addEventListener("blur", async () => {
    const cep = propertyCep.value.replace(/\D/g, "");
    if (realEstate.querySelector("#property-country").value !== "BR" || cep.length !== 8) return;
    try {
      const response = await fetch("https://viacep.com.br/ws/" + cep + "/json/");
      const address = await response.json();
      if (address.erro) return;
      realEstate.querySelector("#property-state").value = address.uf || "";
      realEstate.querySelector("#property-city").value = address.localidade || "";
      realEstate.querySelector("#property-address").value = [address.logradouro, address.bairro].filter(Boolean).join(" — ");
    } catch { /* CEP remains editable for manual completion. */ }
  });
  fixedIncomeDetails?.insertAdjacentHTML(
    "afterbegin",
    '<p id="fi-savings-rule" class="fixed-income-rule" hidden>A remuneração da poupança é calculada automaticamente conforme a regra vigente.</p>',
  );
  const fixedIncomePrincipalLabel = fixedIncomeDetails?.querySelector("#fi-principal")?.closest("label");
  if (fixedIncomePrincipalLabel?.firstChild) fixedIncomePrincipalLabel.firstChild.textContent = "Valor aplicado";
  document.querySelector("#fi-instrument")?.addEventListener("change", event => {
    setFixedIncomeFields();
  });
  document.querySelector("#fi-indexer")?.addEventListener("change", setFixedIncomeFields);
  ["#pension-origin", "#pension-system", "#pension-match-enabled", "#pension-vesting-enabled", "#pension-composition"].forEach(selector => {
    document.querySelector(selector)?.addEventListener("change", setPensionFields);
  });
  const countryInput = document.querySelector("#country");
  countryInput?.setAttribute("list", "country-options");
  countryInput?.insertAdjacentHTML("afterend", '<datalist id="country-options"><option value="Brasil"></option><option value="Estados Unidos"></option><option value="Canadá"></option><option value="Reino Unido"></option><option value="Alemanha"></option><option value="França"></option><option value="Espanha"></option><option value="Itália"></option><option value="Portugal"></option><option value="Japão"></option><option value="Suíça"></option><option value="Austrália"></option></datalist>');
  countryInput?.addEventListener("input", event => {
    const currency = currencyForCountry(event.target.value);
    if (currency) document.querySelector("#currency-code").value = currency;
  });
  countryInput?.addEventListener("blur", event => {
    const currency = currencyForCountry(event.target.value);
    if (currency) document.querySelector("#currency-code").value = currency;
  });
  arrangeOperationForm();
  bindOperationModal();
  bindOperationSearch();
  typeInput?.addEventListener("change", event => {
    setOperationFields(event.target.value);
    document.querySelector("#ticker").loadFixedIncomeSaleOptions?.();
    if (!["BUY", "SELL"].includes(event.target.value)) document.querySelector("#operation-more-options").open = true;
    updateOperationSummary();
    syncQuickOperationButtons();
  });
  document.querySelector("#trade-asset-class")?.addEventListener("change", () => {
    setOperationFields(typeInput.value);
    document.querySelector("#ticker").loadFixedIncomeSaleOptions?.();
    if (["FIXED_INCOME", "PENSION", "REAL_ESTATE"].includes(document.querySelector("#trade-asset-class").value)) {
      document.querySelector("#operation-more-options").open = true;
    }
    updateOperationSummary();
  });
  setOperationFields(typeInput?.value || "BUY");
  document.querySelector("#ticker").loadFixedIncomeSaleOptions?.();
  setFixedIncomeFields();
  syncQuickOperationButtons();
  updateOperationSummary();
  ["#quantity", "#unit_price"].forEach(selector => {
    const input = document.querySelector(selector);
    input?.addEventListener("input", () => { input.setCustomValidity(""); updateOperationSummary(); });
  });
  document.querySelector("#fixed-income-sale-value")?.addEventListener("input", () => {
    document.querySelector("#fixed-income-sale-value").setCustomValidity("");
    updateOperationSummary();
  });
  document.querySelector("#ticker")?.addEventListener("input", updateOperationSummary);
  ["#fi-principal", "#pension-balance", "#property-value", "#dividend-amount", "#external-flow-amount", "#jcp-gross", "#jcp-tax"].forEach(selector => {
    document.querySelector(selector)?.addEventListener("input", updateOperationSummary);
  });
  document.querySelector("#trade-asset-class")?.addEventListener("change", updateOperationSummary);
  setPensionFields();
  form?.addEventListener("submit", async event => {
    event.preventDefault();
    const type = typeInput.value;
    const assetClass = document.querySelector("#trade-asset-class").value;
    const fixedIncomeSale = type === "SELL" && assetClass === "FIXED_INCOME";
    const saleValue = document.querySelector("#fixed-income-sale-value");
    const tickerInput = document.querySelector("#ticker");
    if (fixedIncomeSale) {
      const holdings = await portfolioApi.holdings().catch(() => null);
      const asset = (holdings?.classes || []).find(group => group.asset_class === "FIXED_INCOME")?.assets
        ?.find(item => String(item.ticker).toUpperCase() === tickerInput.value.trim().toUpperCase());
      if (!asset) tickerInput.setCustomValidity("Selecione uma posição aberta de Renda Fixa da carteira.");
      if (!Number.isFinite(Number(saleValue.value)) || Number(saleValue.value) <= 0) {
        saleValue.setCustomValidity("Informe o valor total da venda.");
      }
    }
    const quantityField = document.querySelector("#quantity");
    const priceField = document.querySelector("#unit_price");
    if (quantityField.required && (!Number.isFinite(Number(quantityField.value)) || Number(quantityField.value) <= 0)) {
      quantityField.setCustomValidity("Informe uma quantidade maior que zero.");
    }
    if (priceField.required && (!Number.isFinite(Number(priceField.value)) || Number(priceField.value) <= 0)) {
      priceField.setCustomValidity("Informe o preço da operação.");
    }
    const message = document.querySelector("#message");
    const button = form.querySelector("button[type=submit]");
    const external = ["DEPOSIT", "WITHDRAWAL"].includes(type);
    const fixedIncome = type === "BUY" && assetClass === "FIXED_INCOME";
    const pension = type === "BUY" && assetClass === "PENSION";
    const realEstate = type === "BUY" && assetClass === "REAL_ESTATE";
    const crypto = assetClass === "CRYPTO";
    const quantityInput = document.querySelector("#quantity");
    const priceInput = document.querySelector("#unit_price");
    if (crypto && (!isPositiveDecimal(quantityInput.value) || !isPositiveDecimal(priceInput.value))) {
      const invalidInput = !isPositiveDecimal(quantityInput.value) ? quantityInput : priceInput;
      invalidInput.setCustomValidity("Informe um valor positivo.");
      invalidInput.reportValidity();
      invalidInput.setCustomValidity("");
      return;
    }
    if (!validateForm(form)) return;
    try {
      await withProcessing(button, async () => {
        if (fixedIncomeSale) {
          await portfolioApi.createFixedIncomeSale({
            ticker: tickerInput.value.trim(),
            amount: saleValue.value,
            effective_date: document.querySelector("#effective-date").value,
          });
        } else if (fixedIncome) {
          await portfolioApi.createFixedIncome(wealthPayload("FIXED_INCOME"));
        } else if (pension) {
          const payload = wealthPayload("PENSION");
          const created = await portfolioApi.createPensionPlan(payload);
          if (payload.vehicle_cnpj) {
            await portfolioApi.associatePensionVehicle(created.ticker, {
              vehicle_cnpj: payload.vehicle_cnpj,
              vehicle_name: payload.vehicle_name || null,
            });
          }
        } else if (realEstate) {
          await portfolioApi.createRealEstate(wealthPayload("REAL_ESTATE"));
        } else if (external) {
          await portfolioApi.externalFlow({
            event_type: type,
            amount: document.querySelector("#external-flow-amount").value,
            effective_date: document.querySelector("#effective-date").value,
            capital_flow_type: document.querySelector("#capital-flow-type")?.value || "EXTERNAL_CAPITAL",
          });
        } else {
          const payload = {
            event_type: type,
            ticker: document.querySelector("#ticker").value,
            name: document.querySelector("#ticker").dataset.assetName || null,
            asset_class: document.querySelector("#trade-asset-class").value,
            country: document.querySelector("#country").value,
            currency_code: document.querySelector("#currency-code").value,
            sector: document.querySelector("#sector").value || null,
            quantity: crypto ? decimalForApi(quantityInput.value) : quantityInput.value,
            unit_price: crypto ? decimalForApi(priceInput.value) : priceInput.value,
            effective_date: document.querySelector("#effective-date").value,
            capital_flow_type: document.querySelector("#capital-flow-type")?.value || "UNKNOWN",
            source_asset_class: document.querySelector("#capital-flow-source")?.value || null,
            destination_asset_class: document.querySelector("#trade-asset-class").value,
          };
          if (type === "DIVIDEND") {
            await portfolioApi.dividend({
              ticker: payload.ticker,
              amount: document.querySelector("#dividend-amount").value,
              effective_date: payload.effective_date,
            });
          } else if (type === "INTEREST_ON_EQUITY") {
            await portfolioApi.jcp({
              ticker: payload.ticker,
              gross_amount: document.querySelector("#jcp-gross").value,
              withheld_tax: document.querySelector("#jcp-tax").value,
              effective_date: payload.effective_date,
            });
          } else {
            await portfolioApi.createTrade(payload);
          }
        }
        await Promise.all([loadPortfolio(), loadOperations({ reset: true })]);
      });
      setMessage(message, "Operação registrada com sucesso.");
      document.querySelector("#operation-modal")?.close();
      form.reset();
      document.querySelector("#event_type").value = "BUY";
      document.querySelector("#trade-asset-class").value = "BRAZILIAN_STOCK";
      document.querySelector("#ticker").dataset.assetName = "";
      document.querySelector("#fixed-income-sale-value").value = "";
      document.querySelector("#operation-more-options").open = false;
      setOperationFields("BUY");
      syncQuickOperationButtons();
      updateOperationSummary();
    } catch (error) { setMessage(message, friendlyError(error), "error"); }
  });
  const quoteForm = document.querySelector("#quote-form");
  quoteForm?.addEventListener("submit", async event => {
    event.preventDefault();
    if (!validateForm(quoteForm)) return;
    const message = document.querySelector("#quote-message");
    try {
      await withProcessing(quoteForm.querySelector("button[type=submit]"), async () => {
        await portfolioApi.updatePrice(document.querySelector("#quote-ticker").value, { current_price: document.querySelector("#current-price").value, effective_date: document.querySelector("#quote-date").value });
        await loadPortfolio();
      }, "Atualizando…");
      setMessage(message, "Cotação atualizada.");
    } catch (error) { setMessage(message, friendlyError(error), "error"); }
  });
  quoteForm?.insertAdjacentHTML("beforeend", '<button type="button" class="secondary" id="refresh-prices">Atualizar cotações automaticamente</button><div id="refresh-prices-message" class="message" role="alert"></div>');
  document.querySelector("#refresh-prices")?.addEventListener("click", async event => {
    const message = document.querySelector("#refresh-prices-message");
    try {
      const result = await withProcessing(event.currentTarget, () => portfolioApi.refreshPrices(), "Atualizando…");
      await loadPortfolio();
      const providers = result.providers || [];
      const failures = providers.filter(item => item.status === "FAILED").length;
      setMessage(message, `${result.updated} cotação(ões) atualizada(s). ${result.unavailable.length} indisponível(is).${failures ? ` ${failures} fonte(s) mantiveram a última cotação válida.` : ""}`);
    } catch (error) { setMessage(message, friendlyError(error), "error"); }
  });
  document.querySelector("#clear")?.addEventListener("click", async event => {
    const button = event.currentTarget;
    if (!await confirmDangerousAction()) return;
    try {
      await withProcessing(button, async () => {
        await portfolioApi.resetAllData();
        await loadPortfolio();
      }, "Excluindo…");
      setMessage(document.querySelector("#message"), "Carteira limpa com sucesso.");
    } catch (error) { setMessage(document.querySelector("#message"), friendlyError(error), "error"); }
  });
  const recurringForm = document.querySelector("#recurring-form");
  document.querySelector("#recurring-type")?.addEventListener("change", event => {
    const dividend = event.target.value === "DIVIDEND";
    document.querySelector("#recurring-ticker-label").hidden = !dividend;
    document.querySelector("#recurring-ticker").required = dividend;
  });
  recurringForm?.addEventListener("submit", async event => {
    event.preventDefault();
    if (!validateForm(recurringForm)) return;
    const button = recurringForm.querySelector("button[type=submit]");
    try {
      await withProcessing(button, async () => {
        const result = await portfolioApi.createRecurringRule({
          event_type: document.querySelector("#recurring-type").value,
          amount: document.querySelector("#recurring-amount").value,
          frequency: document.querySelector("#recurring-frequency").value,
          next_execution_date: document.querySelector("#recurring-date").value,
          end_execution_date: document.querySelector("#recurring-end-date").value || null,
          ticker: document.querySelector("#recurring-ticker").value || null,
        });
        await Promise.all([loadRecurringRules(), loadOperations({ reset: true }), loadPortfolio()]);
        setMessage(document.querySelector("#recurring-message"), `Agendamento salvo. ${result.executed} lançamento(s) devido(s) foi(ram) criado(s).`);
        document.querySelector("#recurrence-modal")?.close();
        recurringForm.reset();
      }, "Agendando…");
    } catch (error) { setMessage(document.querySelector("#recurring-message"), friendlyError(error), "error"); }
  });
}

export async function loadOperationsRoute() {
  if (activeOperationsTab === "RECURRING") await loadRecurringRules();
  else await loadOperations();
}

async function loadRecurringRules() {
  const target = document.querySelector("#recurring-list");
  if (!target) return;
  try {
    const data = await portfolioApi.recurringRules();
    target.innerHTML = data.rules.length
      ? table(["Tipo", "Ativo", "Valor", "Frequência", "Próxima execução", "Fim", "Status", ""], data.rules.map(rule => `<tr><td>${recurringTypeLabel(rule.event_type)}</td><td>${rule.ticker || "—"}</td><td>${money(rule.amount)}</td><td>${recurringFrequencyLabel(rule.frequency)}</td><td>${rule.next_execution_date}</td><td>${rule.end_execution_date || "—"}</td><td>${rule.active ? "Ativo" : "Encerrado"}</td><td><button class="edit-recurring" data-rule-id="${rule.id}" type="button">Editar</button>${rule.active ? `<button class="close-recurring secondary" data-rule-id="${rule.id}" type="button">Encerrar</button>` : ""}<button class="delete-recurring secondary" data-rule-id="${rule.id}" type="button">Excluir</button></td></tr>`))
      : emptyState("Nenhuma recorrência agendada.");
    const rules = new Map(data.rules.map(rule => [rule.id, rule]));
    target.querySelectorAll(".edit-recurring").forEach(button => button.addEventListener("click", () => openRecurringEditor(rules.get(button.dataset.ruleId))));
    target.querySelectorAll(".close-recurring").forEach(button => button.addEventListener("click", () => closeRecurringRule(button.dataset.ruleId)));
    target.querySelectorAll(".delete-recurring").forEach(button => button.addEventListener("click", () => deleteRecurringRule(button.dataset.ruleId)));
  } catch (error) { target.textContent = friendlyError(error); }
}

const recurringTypeLabel = type => ({ DEPOSIT: "Aporte", WITHDRAWAL: "Retirada", DIVIDEND: "Provento" }[type] || type);
const recurringFrequencyLabel = frequency => ({ MONTHLY: "Mensal", QUARTERLY: "Trimestral", YEARLY: "Anual" }[frequency] || frequency);

function openRecurringEditor(rule) {
  if (!rule) return;
  const dialog = document.createElement("dialog");
  dialog.className = "allocation-policy-dialog";
  dialog.innerHTML = `<form method="dialog"><div class="dialog-heading"><div><h2>Editar agendamento</h2><p>Os próximos lançamentos seguirão estes dados. Ocorrências já geradas não serão alteradas.</p></div><button class="dialog-close" value="cancel" aria-label="Fechar">×</button></div><div class="policy-inputs"><label>Valor<input id="recurring-edit-amount" type="number" min="0.01" step="0.01" value="${rule.amount}" required></label><label>Frequência<select id="recurring-edit-frequency"><option value="MONTHLY">Mensal</option><option value="QUARTERLY">Trimestral</option><option value="YEARLY">Anual</option></select></label><label>Fim da execução (opcional)<input id="recurring-edit-end-date" type="date" value="${rule.end_execution_date || ""}"></label><div class="message" id="recurring-edit-message" role="alert"></div></div><div class="dialog-actions"><button class="secondary" value="cancel">Cancelar</button><button id="save-recurring-edit" type="button">Salvar alterações</button></div></form>`;
  document.body.append(dialog);
  dialog.querySelector("#recurring-edit-frequency").value = rule.frequency;
  dialog.querySelector("#save-recurring-edit").addEventListener("click", async event => {
    const button = event.currentTarget;
    const amount = dialog.querySelector("#recurring-edit-amount");
    if (!amount.reportValidity()) return;
    try {
      const result = await withProcessing(button, () => portfolioApi.updateRecurringRule(rule.id, {
        amount: amount.value,
        frequency: dialog.querySelector("#recurring-edit-frequency").value,
        end_execution_date: dialog.querySelector("#recurring-edit-end-date").value || null,
      }));
      await Promise.all([loadRecurringRules(), loadOperations({ reset: true }), loadPortfolio()]);
      setMessage(document.querySelector("#recurring-message"), `Agendamento atualizado. ${result.executed} lançamento(s) devido(s) foi(ram) criado(s).`);
      dialog.close();
    } catch (error) { setMessage(dialog.querySelector("#recurring-edit-message"), friendlyError(error), "error"); }
  });
  dialog.addEventListener("close", () => dialog.remove());
  dialog.showModal();
}

async function closeRecurringRule(ruleId) {
  try {
    const result = await portfolioApi.closeRecurringRule(ruleId);
    await Promise.all([loadRecurringRules(), loadOperations({ reset: true }), loadPortfolio()]);
    setMessage(document.querySelector("#recurring-message"), `Agendamento encerrado. ${result.executed} lançamento(s) devido(s) foi(ram) criado(s).`);
  } catch (error) { setMessage(document.querySelector("#recurring-message"), friendlyError(error), "error"); }
}

async function deleteRecurringRule(ruleId) {
  if (!await confirmRecurringDeletion()) return;
  try {
    await portfolioApi.deleteRecurringRule(ruleId);
    await loadRecurringRules();
    setMessage(document.querySelector("#recurring-message"), "Agendamento excluído. Lançamentos já gerados foram preservados.");
  } catch (error) { setMessage(document.querySelector("#recurring-message"), friendlyError(error), "error"); }
}

function confirmRecurringDeletion() {
  return new Promise(resolve => {
    const dialog = document.createElement("dialog");
    dialog.className = "confirm-dialog";
    dialog.innerHTML = '<form method="dialog"><h2>Excluir agendamento?</h2><p>Apenas a regra de recorrência será removida. Lançamentos já gerados permanecerão na carteira.</p><div class="dialog-actions"><button value="cancel" class="secondary">Cancelar</button><button value="confirm" class="destructive">Excluir agendamento</button></div></form>';
    dialog.addEventListener("close", () => { resolve(dialog.returnValue === "confirm"); dialog.remove(); });
    document.body.append(dialog);
    dialog.showModal();
  });
}

let importHistoryOffset = 0;
let importHistoryRequestId = 0;
async function loadB3ImportHistory(reset = false) {
  const target = document.querySelector("#operations-import-history");
  if (!target) return;
  if (reset) importHistoryOffset = 0;
  const requestId = ++importHistoryRequestId;
  target.innerHTML = "<p class='empty' aria-busy='true'>Carregando histórico…</p>";
  try {
    const data = await portfolioApi.b3ImportHistory(importHistoryOffset, 20);
    if (requestId !== importHistoryRequestId) return;
    if (!data.items.length && importHistoryOffset === 0) { target.innerHTML = emptyState("Nenhuma importação B3 aplicada ainda."); return; }
    target.innerHTML = `<div class="import-history-list">${data.items.map(batch => `<article class="import-history-item"><div><strong>${escapeAttribute(batch.file_name)}</strong><small>${escapeAttribute(new Date(batch.created_at).toLocaleString("pt-BR"))} · ${escapeAttribute(batch.report_type)}</small></div><span>${escapeAttribute(batch.status)}</span><p>${batch.total_rows} linhas · ${batch.new_rows} novas · ${batch.duplicate_rows} duplicadas · ${batch.review_rows} para revisão · ${batch.invalid_rows} inválidas</p></article>`).join("")}</div><p class="history-loaded-count">Mostrando ${importHistoryOffset + data.items.length} de ${data.total}</p>${data.has_more ? "<button class='secondary history-load-more' type='button' data-import-history-more>Carregar mais</button>" : ""}`;
    importHistoryOffset += data.items.length;
    target.querySelector("[data-import-history-more]")?.addEventListener("click", () => loadB3ImportHistory(false));
  } catch (error) { if (requestId === importHistoryRequestId) target.textContent = friendlyError(error); }
}

const OPERATIONS_PAGE_SIZE = 20;
const operationsTabs = new Map(["ALL", "MOVEMENTS", "INCOME"].map(key => [key, {
  offset: 0,
  items: [],
  total: 0,
  hasMore: false,
  groups: new Map(),
  loaded: false,
  filters: { period: "ALL", asset_class: "", event_type: "", search: "", start_date: "", end_date: "" },
  requestId: 0,
  searchTimer: null,
}]));
let activeOperationsTab = "ALL";

export function selectOperationsTab(tab) {
  if (tab === "RECURRING") {
    activeOperationsTab = tab;
    syncOperationsTabs(tab);
    document.querySelector("#operations-panel").hidden = true;
    document.querySelector("#recurring-panel").hidden = false;
    loadRecurringRules();
    return;
  }
  if (!operationsTabs.has(tab)) return;
  activeOperationsTab = tab;
  syncOperationsTabs(tab);
  document.querySelector("#operations-panel").hidden = false;
  document.querySelector("#recurring-panel").hidden = true;
  const state = operationsTabs.get(tab);
  if (state.loaded) renderOperationsState(tab, state);
  else loadOperations();
}

function syncOperationsTabs(tab) {
  document.querySelectorAll("[data-operations-tab]").forEach(button => {
    const selected = button.dataset.operationsTab === tab;
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected ? 0 : -1;
  });
}

function resetOperationsState(state) {
  state.offset = 0;
  state.items = [];
  state.total = 0;
  state.hasMore = false;
  state.groups = new Map();
  state.loaded = false;
  state.requestId += 1;
}

export async function loadOperations({ reset = false } = {}) {
  const target = document.querySelector("#operations-history");
  const filtersTarget = document.querySelector("#operations-filter-controls");
  const state = operationsTabs.get(activeOperationsTab);
  if (!target || !state) return;
  const tab = activeOperationsTab;
  if (reset) resetOperationsState(state);
  if (state.loaded && !reset) { renderOperationsState(tab, state); return; }
  const requestId = ++state.requestId;
  target.innerHTML = "<p class='empty' aria-busy='true'>Carregando lançamentos…</p>";
  try {
    const data = await portfolioApi.operationsHistory({
      ...readHistoryFilters(state.filters),
      movement_type: tab === "MOVEMENTS" ? "MOVEMENTS" : tab === "INCOME" ? "INCOME" : "",
      event_type: state.filters.event_type,
      group_by: tab === "ALL" ? "DATE" : "TYPE",
      offset: 0,
      page_size: OPERATIONS_PAGE_SIZE,
    });
    if (requestId !== state.requestId || tab !== activeOperationsTab) return;
    state.availableClasses = data.available_classes || [];
    if (tab === "ALL") {
      const group = data.groups[0] || {};
      state.items = group.events || [];
      state.offset = state.items.length;
      state.total = group.total ?? group.event_count ?? 0;
      state.hasMore = Boolean(group.has_more);
    } else {
      state.groups = new Map((data.groups || []).map(group => [group.key, {
        ...group,
        items: group.events || [],
        loaded: (group.events || []).length,
        cursor: group.next_cursor,
        hasMore: Boolean(group.has_more),
        collapsed: false,
        requestId: 0,
      }]));
      state.total = data.total_count || 0;
    }
    state.loaded = true;
    renderOperationsState(tab, state);
  } catch (error) {
    if (requestId === state.requestId) target.textContent = friendlyError(error);
  }
}

function renderOperationsState(tab, state) {
  const target = document.querySelector("#operations-history");
  const filtersTarget = document.querySelector("#operations-filter-controls");
  if (!target) return;
  if (filtersTarget) {
    filtersTarget.innerHTML = renderHistoryFilters(state.filters, state.availableClasses, tab);
    bindHistoryControls(filtersTarget, state);
  }
  if (tab === "ALL") {
    target.innerHTML = state.items.length ? renderTimeline(state.items) : emptyState("Nenhum lançamento encontrado para estes filtros.");
    target.insertAdjacentHTML("beforeend", `<p class="history-loaded-count">Mostrando ${state.items.length} de ${state.total}</p>`);
    if (state.hasMore) target.insertAdjacentHTML("beforeend", "<button type='button' class='secondary history-load-more' data-load-all-more>Carregar mais</button>");
    target.querySelector("[data-load-all-more]")?.addEventListener("click", () => loadMoreAll(tab, state));
    bindRenderedDeleteButtons(target);
    return;
  }
  if (!state.groups.size) {
    target.innerHTML = emptyState("Nenhum lançamento encontrado para estes filtros.");
    return;
  }
  target.innerHTML = [...state.groups.values()].map(renderOperationTypeGroup).join("");
  target.querySelectorAll("[data-toggle-operation-group]").forEach(button => button.addEventListener("click", () => {
    const group = state.groups.get(button.dataset.toggleOperationGroup);
    if (!group) return;
    group.collapsed = !group.collapsed;
    renderOperationsState(tab, state);
  }));
  target.querySelectorAll("[data-load-operation-group]").forEach(button => button.addEventListener("click", () => loadMoreGroup(tab, state, button.dataset.loadOperationGroup)));
  bindRenderedDeleteButtons(target);
}

async function loadMoreAll(tab, state) {
  const requestId = state.requestId;
  const data = await portfolioApi.operationsHistory({
    ...readHistoryFilters(state.filters), group_by: "DATE", offset: state.offset,
    page_size: OPERATIONS_PAGE_SIZE,
  });
  if (requestId !== state.requestId || tab !== activeOperationsTab) return;
  const group = data.groups[0] || {};
  state.items.push(...(group.events || []));
  state.offset += (group.events || []).length;
  state.total = group.total ?? state.total;
  state.hasMore = Boolean(group.has_more);
  renderOperationsState(tab, state);
}

async function loadMoreGroup(tab, state, groupKey) {
  const group = state.groups.get(groupKey);
  if (!group || !group.hasMore || group.loading) return;
  group.loading = true;
  const requestId = ++group.requestId;
  try {
    const data = await portfolioApi.operationsHistory({
      ...readHistoryFilters(state.filters),
      movement_type: tab === "MOVEMENTS" ? "MOVEMENTS" : "INCOME",
      event_type: state.filters.event_type,
      group_by: "TYPE", group_key: groupKey,
      offset: group.loaded, page_size: OPERATIONS_PAGE_SIZE,
    });
    if (requestId !== group.requestId || tab !== activeOperationsTab || state.groups.get(groupKey) !== group) return;
    const next = data.groups.find(item => item.key === groupKey);
    if (!next) { group.hasMore = false; return; }
    group.items.push(...(next.events || []));
    group.loaded = group.items.length;
    group.cursor = next.next_cursor;
    group.hasMore = Boolean(next.has_more);
    group.event_count = next.total ?? next.event_count;
    group.moved_amount = next.moved_amount;
  } catch (error) {
    setMessage(document.querySelector("#operations-message"), friendlyError(error), "error");
  } finally {
    group.loading = false;
    if (tab === activeOperationsTab) renderOperationsState(tab, state);
  }
}

function renderOperationTypeGroup(group) {
  const count = Number(group.total ?? group.event_count ?? group.items.length);
  const amount = group.moved_amount == null ? "" : `<strong class="operation-group-amount">${money(group.moved_amount, "BRL")}</strong>`;
  const content = group.collapsed ? "" : `<div class="operation-type-group-content"><div class="timeline-day-items">${group.items.map(renderTimelineItem).join("")}</div><p class="history-loaded-count">Mostrando ${group.items.length} de ${count}</p>${group.hasMore ? `<button type="button" class="secondary history-load-more" data-load-operation-group="${escapeAttribute(group.key)}">Carregar mais</button>` : ""}</div>`;
  return `<section class="operation-type-group"><button type="button" class="operation-type-group-heading" data-toggle-operation-group="${escapeAttribute(group.key)}" aria-expanded="${!group.collapsed}"><span>${escapeAttribute(group.label)}</span><span>${count} lançamentos</span>${amount}<span class="operation-group-collapse">${group.collapsed ? "Expandir" : "Recolher"}</span></button>${content}</section>`;
}

function bindRenderedDeleteButtons(target) {
  target.querySelectorAll(".delete-operation").forEach(button => button.addEventListener("click", async () => {
    if (!await confirmOperationDeletion()) return;
    await withProcessing(button, async () => {
      await portfolioApi.deleteOperation(button.dataset.operationId);
      await Promise.all([loadOperations({ reset: true }), loadPortfolio()]);
    }, "Excluindo…");
  }));
}

function readHistoryFilters(filters) {
  const { period, asset_class, search, start_date, end_date } = filters;
  if (period === "CUSTOM") return { asset_class, search, start_date, end_date };
  const days = { "30D": 30, "3M": 91, "6M": 183, "12M": 365, "2Y": 730, "5Y": 1826 }[period];
  const from = days ? new Date(Date.now() - days * 86400000).toISOString().slice(0, 10) : "";
  return { asset_class, search, start_date: from, end_date: "" };
}

function renderHistoryFilters(filters, classes, tab) {
  const commonTypes = [["", "Todos os tipos"], ["BUY", "Compra"], ["SELL", "Venda"], ["DEPOSIT", "Aporte"], ["WITHDRAWAL", "Retirada"], ["SPLIT", "Desdobramento"], ["REVERSE_SPLIT", "Grupamento"], ["BONUS_SHARE", "Bonificação"], ["SUBSCRIPTION", "Subscrição"], ["APPLICATION", "Aplicação"], ["REDEMPTION", "Resgate"], ["BROKERAGE_FEE", "Corretagem"], ["TAX", "Imposto"], ["FX_EXCHANGE", "Câmbio"], ["STAKING_REWARD", "Recompensa de staking"], ["DIVIDEND", "Dividendos"], ["INTEREST_ON_EQUITY", "JCP"], ["FII_INCOME", "Rendimentos de FII"], ["FIXED_INCOME_INTEREST", "Juros de renda fixa"]];
  const types = tab === "INCOME" ? [["", "Todos os rendimentos"], ...commonTypes.slice(-4).reverse()] : commonTypes;
  const option = (value, label, current) => "<option value='" + escapeAttribute(value) + "'" + (value === current ? " selected" : "") + ">" + escapeAttribute(label) + "</option>";
  const periodOptions = [["ALL", "Tudo"], ["30D", "30 dias"], ["3M", "3 meses"], ["6M", "6 meses"], ["12M", "12 meses"], ["2Y", "2 anos"], ["5Y", "5 anos"], ["CUSTOM", "Personalizado"]];
  const hasFilters = filters.period !== "ALL" || filters.asset_class || filters.event_type || filters.search || filters.start_date || filters.end_date;
  return "<div class='history-filters'><label>Buscar ativo<input id='history-search' type='search' placeholder='PETR4, WEG, IVV…' value='" + escapeAttribute(filters.search) + "'></label>"
    + "<label>Tipo<select id='history-event-type'>" + types.map(item => option(item[0], item[1], filters.event_type)).join("") + "</select></label>"
    + "<label>Classe<select id='history-class'>" + option("", "Todas as classes", filters.asset_class) + classes.map(item => option(item.key, item.label, filters.asset_class)).join("") + "</select></label>"
    + "<label>Período<select id='history-period'>" + periodOptions.map(item => option(item[0], item[1], filters.period)).join("") + "</select></label>"
    + "<button id='clear-history-filters' class='secondary' type='button' " + (hasFilters ? "" : "hidden") + ">Limpar filtros</button></div>"
    + "<div id='history-custom-dates' class='history-custom-dates' " + (filters.period === "CUSTOM" ? "" : "hidden") + "><label>Data inicial<input id='history-start-date' type='date' value='" + filters.start_date + "'></label><label>Data final<input id='history-end-date' type='date' value='" + filters.end_date + "'></label></div>";
}

function bindHistoryControls(target, state) {
  const update = () => { resetOperationsState(state); loadOperations(); };
  [["#history-period", "period"], ["#history-class", "asset_class"], ["#history-event-type", "event_type"], ["#history-start-date", "start_date"], ["#history-end-date", "end_date"]].forEach(([selector, key]) => {
    target.querySelector(selector)?.addEventListener("change", event => {
      state.filters[key] = event.target.value;
      if (key === "period") target.querySelector("#history-custom-dates").hidden = event.target.value !== "CUSTOM";
      update();
    });
  });
  target.querySelector("#history-search")?.addEventListener("input", event => {
    state.filters.search = event.target.value;
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(update, 250);
  });
  target.querySelector("#clear-history-filters")?.addEventListener("click", () => {
    state.filters = { period: "ALL", asset_class: "", event_type: "", search: "", start_date: "", end_date: "" };
    update();
  });
}

function renderTimeline(events) {
  if (!events.length) return emptyState("Nenhum lançamento encontrado para estes filtros.");
  const months = new Map();
  events.sort((left, right) => right.effective_date.localeCompare(left.effective_date) || String(right.registered_at).localeCompare(String(left.registered_at)));
  events.forEach(event => {
    const month = event.effective_date.slice(0, 7);
    const days = months.get(month) || new Map();
    const dayEvents = days.get(event.effective_date) || [];
    dayEvents.push(event);
    days.set(event.effective_date, dayEvents);
    months.set(month, days);
  });
  return Array.from(months.entries()).map(([month, days]) =>
    "<section class='timeline-month'><h2>" + formatMonth(month) + "</h2>"
    + Array.from(days.entries()).map(([day, items]) =>
      "<div class='timeline-day'><h3>" + formatHistoryDate(day) + "</h3><div class='timeline-day-items'>"
      + items.map(renderTimelineItem).join("") + "</div></div>"
    ).join("") + "</section>"
  ).join("");
}

function renderTimelineItem(item) {
  const identity = item.ticker || item.asset_name || item.operation;
  const details = [item.operation, item.quantity !== null && item.quantity !== undefined ? item.quantity + " un." : "", item.unit_price !== null && item.unit_price !== undefined ? "a " + money(item.unit_price, item.currency_code) : ""].filter(Boolean).join(" · ");
  return "<article class='timeline-item'><div class='timeline-item-identity'><strong>" + escapeAttribute(identity) + "</strong>"
    + (item.asset_name && item.ticker ? "<small>" + escapeAttribute(item.asset_name) + "</small>" : "") + "</div>"
    + "<div class='timeline-item-description'><span>" + escapeAttribute(details) + "</span><small>" + escapeAttribute(item.source || "—") + "</small></div>"
    + "<strong class='timeline-item-value'>" + (item.amount === null || item.amount === undefined ? "—" : money(item.amount, item.currency_code)) + "</strong>"
    + historyDeleteButton(item.id) + "</article>";
}

function formatMonth(value) {
  const [year,month] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric" }).format(new Date(year,month-1,1));
}

function historyColumns(kind) {
  if (kind === "income") return ["Ativo", "Tipo", "Valor", "Data", "Fonte", ""];
  if (kind === "cash") return ["Tipo", "Valor", "Data", "Fonte", ""];
  if (kind === "fixed_income") return ["Produto", "Instrumento", "Indexador", "Operação", "Valor", "Taxa / condição", "Data", "Vencimento", "Fonte", ""];
  if (kind === "pension") return ["Plano", "Operação", "Origem", "Valor", "Data", "Fonte", ""];
  if (kind === "real_estate") return ["Imóvel", "Operação", "Valor", "Data", "Fonte", ""];
  return ["Ativo", "Operação", "Quantidade", "Preço unitário", "Valor", "Data", "Fonte", ""];
}

function historyRow(kind, item) {
  const identity = `<strong>${item.ticker || item.asset_name || "—"}</strong>${item.asset_name && item.ticker ? `<small>${item.asset_name}</small>` : ""}`;
  const deleteButton = historyDeleteButton(item.id);
  if (kind === "income") return `<tr><td>${item.ticker || item.asset_name || "—"}</td><td>${item.operation}</td><td>${money(item.amount, item.currency_code)}</td><td>${formatHistoryDate(item.effective_date)}</td><td>${item.source}</td><td>${deleteButton}</td></tr>`;
  if (kind === "cash") return `<tr><td>${item.operation}</td><td>${money(item.amount, item.currency_code)}</td><td>${formatHistoryDate(item.effective_date)}</td><td>${item.source}</td><td>${deleteButton}</td></tr>`;
  if (kind === "fixed_income") return `<tr><td>${item.asset_name || item.ticker || "—"}</td><td>${item.instrument || "—"}</td><td>${item.indexer || "—"}</td><td>${item.operation}</td><td>${money(item.amount, item.currency_code)}</td><td>${item.condition || "—"}</td><td>${formatHistoryDate(item.effective_date)}</td><td>${formatHistoryDate(item.maturity_date)}</td><td>${item.source}</td><td>${deleteButton}</td></tr>`;
  if (kind === "pension") return `<tr><td>${identity}</td><td>${item.operation}</td><td>—</td><td>${money(item.amount, item.currency_code)}</td><td>${formatHistoryDate(item.effective_date)}</td><td>${item.source}</td><td>${deleteButton}</td></tr>`;
  if (kind === "real_estate") return `<tr><td>${identity}</td><td>${item.operation}</td><td>${money(item.amount, item.currency_code)}</td><td>${formatHistoryDate(item.effective_date)}</td><td>${item.source}</td><td>${deleteButton}</td></tr>`;
  return `<tr><td>${identity}</td><td>${item.operation}</td><td>${item.quantity ?? "—"}</td><td>${item.unit_price === null ? "—" : money(item.unit_price, item.currency_code)}</td><td>${money(item.amount, item.currency_code)}</td><td>${formatHistoryDate(item.effective_date)}</td><td>${item.source}</td><td>${deleteButton}</td></tr>`;
}

function fixedIncomeContractRows(events, columnCount) {
  const contracts = new Map();
  events.forEach(item => {
    const key = item.contract_key || item.id;
    const current = contracts.get(key) || { label: item.contract_label || item.asset_name || item.ticker || "Produto", amount: 0, items: [] };
    current.amount += Number(item.amount);
    current.items.push(item);
    contracts.set(key, current);
  });
  return Array.from(contracts.values()).flatMap(contract => [
    `<tr class="fixed-income-contract"><td colspan="${columnCount}"><strong>${contract.label}</strong><span>${money(contract.amount)} movimentados</span></td></tr>`,
    ...contract.items.map(item => historyRow("fixed_income", item)),
  ]);
}

const historyDeleteButton = id => `<button class="delete-operation secondary" data-operation-id="${id}" type="button">Excluir</button>`;
const formatHistoryDate = value => value ? value.split("-").reverse().join("/") : "—";
