import { bindPortfolioFilters, loadPortfolio } from "./features/portfolio.js?v=20261008-twr-methodology";
import { bindOperations, loadOperationsRoute } from "./features/operations.js?v=20261018-fixed-income-sale-v2";
import { bindPerformance, loadExplanation } from "./features/performance.js?v=20261017-performance-indices-v1";
import { bindSimulation } from "./features/simulation.js?v=20260924-experience-v2";
import { bindBenchmark } from "./features/benchmark.js?v=20260924-route-scoped-v1";
import { bindAttentionCenter, loadAttentionCenter } from "./features/attention-center.js?v=20260924-route-scoped-v1";
import { renderDiversification } from "./features/diversification.js";
import { loadStrategy } from "./features/strategy.js?v=20261017-class-allocation-fix-v1";
import { bindAssetDiscovery } from "./features/asset-discovery.js?v=20260924-route-scoped-v1";
import { setTodayAsDefault } from "./shared/dates.js";
import { setupMethodologyPage } from "./features/methodology.js?v=20261008-twr-methodology";
import { bindNavigation } from "./features/navigation.js?v=20261008-twr-methodology";
import { bindFx } from "./features/fx.js?v=20260924-route-scoped-v1";
import { renderDataSources } from "./features/data-sources.js?v=20260924-route-scoped-v1";
import { bindPaidIncomeSettings } from "./features/paid-income-settings.js";
import { bindMarketPriceSettings } from "./features/market-price-settings.js";
import {
  loadMagicFormulaFiisRoute,
  loadMagicFormulaStocksRoute,
  loadTools,
  setupToolsRoutes,
} from "./features/tools.js?v=20260924-route-scoped-v1";
import { createRouteLifecycle } from "./shared/route-lifecycle.js";
import { beginRouteResourceCycle } from "./shared/resources.js";
import { setupPortfolioContext } from "./features/portfolios.js";
import { setupWalletSettings } from "./features/wallet-settings.js";

let operationsSetup = false;
let settingsSetup = false;

function setupOperations() {
  if (operationsSetup) return;
  operationsSetup = true;
  bindOperations();
  bindAssetDiscovery();
  setTodayAsDefault();
}

async function loadOperationsPage() {
  setupOperations();
  return loadOperationsRoute();
}

function setupSettings() {
  if (settingsSetup) return;
  settingsSetup = true;
  bindFx();
  bindBenchmark();
  bindMarketPriceSettings();
}

async function loadSettingsPage() {
  setupSettings();
  return Promise.allSettled([renderDataSources(), bindPaidIncomeSettings()]);
}

function loadUnderstandPage() {
  bindPerformance();
  return loadExplanation();
}

const routeLoaders = {
  "minha-carteira": () => loadPortfolio("", { refreshAttention: false }),
  entender: loadUnderstandPage,
  estrategia: loadStrategy,
  "risco-exposicao": renderDiversification,
  simular: bindSimulation,
  operacoes: loadOperationsPage,
  configuracoes: loadSettingsPage,
  "carteira-configuracoes": loadWalletSettings,
  ferramentas: loadTools,
  "tools-magic-formula-stocks": loadMagicFormulaStocksRoute,
  "tools-magic-formula-fiis": loadMagicFormulaFiisRoute,
  "ajuda-metodologia": () => {},
};

const lifecycle = createRouteLifecycle({
  loaders: routeLoaders,
  globalLoader: loadAttentionCenter,
  beginCycle: beginRouteResourceCycle,
});

window.addEventListener("DOMContentLoaded", () => {
  window.portfolioLoad = loadPortfolio;
  setupToolsRoutes();
  setupMethodologyPage();
  bindOperations();
  bindAttentionCenter();
  bindPortfolioFilters();
  setTodayAsDefault();
  document.addEventListener("income:routechange", event => {
    lifecycle.activate(event.detail.route).then(result => {
      result.results.forEach(outcome => {
        if (outcome.status === "rejected") console.error(`Falha ao carregar ${result.route}`, outcome.reason);
      });
    });
  });
  setupPortfolioContext(lifecycle).then(() => bindNavigation()).catch(error => {
    console.error("Não foi possível carregar as carteiras", error);
  });
  setupWalletSettings();
});
