from pathlib import Path

STATIC = Path("src/income_analytics/api/static")


def test_dashboard_uses_only_the_modular_javascript_entrypoint() -> None:
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    assert 'type="module" src="/static/js/app-entry.js"' in page
    entry = (STATIC / "js/app-entry.js").read_text(encoding="utf-8")
    assert 'await authRequest("/me")' in entry
    assert 'await import("./app.js")' in entry
    assert "legacy-dashboard.js" not in page


def test_frontend_client_centralizes_the_feature_endpoints() -> None:
    client = (STATIC / "js/api.js").read_text(encoding="utf-8")
    assert "assetAllocationPolicy" in client
    assert "portfolio/intelligence" in client
    assert "rebalancing/assets" in client


def test_frontend_propagates_and_selects_the_active_portfolio() -> None:
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    client = (STATIC / "js/api.js").read_text(encoding="utf-8")
    context = (STATIC / "js/features/portfolios.js").read_text(encoding="utf-8")
    wallet_settings = (STATIC / "js/features/wallet-settings.js").read_text(encoding="utf-8")
    assert 'id="portfolio-menu-trigger"' in page
    assert 'id="portfolio-options"' in page
    assert 'id="portfolio-settings"' in page or 'class="portfolio-settings"' in page
    assert 'href="#carteira-configuracoes"' in page
    assert 'data-page="carteira-configuracoes"' in page
    assert 'id="portfolio-create"' in page
    assert 'id="wallet-name-form"' in page
    assert 'data-wallet-theme="light"' in page
    assert 'data-wallet-theme="dark"' in page
    assert "Compartilhamento indisponível" in page
    assert 'href="#configuracoes" data-navigate title="Configurações"' in page
    assert 'localStorage.getItem("income.activePortfolioId")' in client
    assert 'headers.set("X-Portfolio-Id", portfolioId)' in client
    assert "localStorage.setItem(STORAGE_KEY, id)" in context
    assert 'currentName.textContent = selected?.name || "Carteira"' in context
    assert 'option.setAttribute("aria-selected", String(item.id === current))' in context
    assert 'lifecycle.activate(route)' in context
    assert 'income.portfolioThemes.v1' in wallet_settings
    assert 'portfolioApi.renamePortfolio(id, name)' in wallet_settings
    assert 'document.documentElement.dataset.theme' in wallet_settings


def test_magic_formula_page_uses_persisted_ranking_and_transparent_screening() -> None:
    tools = (STATIC / "js/features/tools.js").read_text(encoding="utf-8")
    client = (STATIC / "js/api.js").read_text(encoding="utf-8")
    styles = (STATIC / "css/app.css").read_text(encoding="utf-8")
    assert "<h1>Fórmula Mágica</h1>" in tools
    assert "Ocultar varejo tradicional" in tools
    assert "Ocultar aviação" in tools
    assert "ranking global preservado após filtros" in tools
    assert "Nenhuma empresa encontrada com os filtros atuais." in tools
    assert "Como funciona?" in tools
    assert "magicFormulaStockDetail" in tools and "openCompanyDetail" in tools
    assert "Ver empresa" in tools and "Setor" in tools
    assert "Por que está nesta posição?" in tools
    assert "data-mf-detail-retry" in tools and "Tentar novamente" in tools
    assert "mf-company-drawer" in styles and "mf-detail-metrics" in styles
    assert "Ranking em: ${rankingDate}" in tools
    assert "informações públicas disponíveis até ${financialCutoff}" in tools
    assert 'data.status === "NO_PUBLISHED_RANKING"' in tools
    assert "O ranking ainda não está disponível." in tools
    assert "data-mf-retry" in tools and "Tentar novamente" in tools
    assert "INVALID_MAGIC_FORMULA_RESPONSE" in tools
    assert "controller.abort()" in (STATIC / "js/api.js").read_text(encoding="utf-8")
    assert "exclude_retail" in client and "exclude_aviation" in client
    assert ".mf-mobile-cards" in styles


def test_operations_exposes_the_auditable_b3_preview_and_apply_flow() -> None:
    client = (STATIC / "js/api.js").read_text(encoding="utf-8")
    operations = (STATIC / "js/features/operations.js").read_text(encoding="utf-8")
    assert 'previewB3Import: payload => request("/imports/b3/preview"' in client
    assert (
        "applyB3Import: batchId => request(`/imports/b3/${encodeURIComponent(batchId)}/apply`"
    ) in client
    assert 'id="b3-import-card"' in operations
    assert 'id="b3-workbook"' in operations
    assert "portfolioApi.previewB3Import" in operations
    assert "portfolioApi.applyB3Import" in operations
    assert "preview.counts" in operations
    assert "REVIEW_REQUIRED" in operations


def test_dashboard_has_loading_and_error_states_for_initial_loading() -> None:
    portfolio = (STATIC / "js/features/portfolio.js").read_text(encoding="utf-8")
    assert "loadingState" in portfolio
    assert "errorState" in portfolio
    assert "catch (error)" in portfolio


def test_entender_explains_partial_historical_valuation_without_hiding_positions() -> None:
    performance = (STATIC / "js/features/performance.js").read_text(encoding="utf-8")
    assert "Ranking parcial." in performance
    assert "sem contribuição calculável foram separados" in performance
    assert "Valores pendentes não foram tratados como zero." in performance


def test_entender_v4_uses_the_question_led_wealth_analysis_journey() -> None:
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    performance = (STATIC / "js/features/performance.js").read_text(encoding="utf-8")
    client = (STATIC / "js/api.js").read_text(encoding="utf-8")
    assert 'id="wealth-period-summary"' in page
    assert 'id="understand-questions"' in page
    assert 'id="wealth-explanation"' in page
    assert "Quanto minha renda fixa valorizou?" in performance
    assert "O que fez meu patrimônio aumentar ou diminuir?" in performance
    assert "Quais investimentos geraram mais renda?" in performance
    assert "Quais investimentos mais ganharam ou perderam valor?" in performance
    assert "Risco no período" not in page
    assert "portfolioApi.wealthExplanation(start, end)" in performance
    assert "portfolioApi.performanceComparison" not in performance
    assert "historyRange" in client
    assert "portfolioApi.historyRange(start, end)" not in performance


def test_holdings_offer_a_lazy_accessible_asset_transactions_modal() -> None:
    client = (STATIC / "js/api.js").read_text(encoding="utf-8")
    portfolio = (STATIC / "js/features/portfolio.js").read_text(encoding="utf-8")
    styles = (STATIC / "css/app.css").read_text(encoding="utf-8")
    assert "assetTransactions: (assetId, params = {})" in client
    assert "/portfolio/assets/${encodeURIComponent(assetId)}/transactions" in client
    assert "data-asset-options" in portfolio
    assert 'aria-haspopup="menu"' in portfolio
    assert "data-asset-transactions" in portfolio
    assert "openAssetTransactions" in portfolio
    assert "assetTransactions(dialog.dataset.assetId" in portfolio
    assert "Nenhum rendimento registrado para este ativo." in portfolio
    assert "Nenhuma movimentação registrada para este ativo." in portfolio
    assert 'role="tablist" aria-label="Tipos de lançamentos"' in portfolio
    assert "data-confirm-asset-delete" in portfolio
    assert "Não foi possível carregar os lançamentos." in portfolio
    assert "assetTransactionsTrigger?.focus()" in portfolio
    assert "asset-transactions-dialog" in styles


def test_holdings_offer_a_read_model_group_distribution_chart() -> None:
    portfolio = (STATIC / "js/features/portfolio.js").read_text(encoding="utf-8")
    styles = (STATIC / "css/app.css").read_text(encoding="utf-8")
    assert "data-group-distribution" in portfolio
    assert "openGroupDistribution" in portfolio
    assert "group.market_value" in portfolio
    assert "asset.marketValue / total * 100" in portfolio
    assert "sort((left, right) => right.marketValue - left.marketValue)" in portfolio
    assert "loadECharts" in portfolio
    assert "groupDistributionTrigger?.focus()" in portfolio
    assert "group-distribution-dialog" in styles
    assert "group-distribution-layout" in styles


def test_minha_carteira_uses_the_consolidated_dashboard_read_model() -> None:
    client = (STATIC / "js/api.js").read_text(encoding="utf-8")
    portfolio = (STATIC / "js/features/portfolio.js").read_text(encoding="utf-8")
    assert 'dashboard: () => request("/portfolio/dashboard")' in client
    assert "await portfolioApi.dashboard()" in portfolio
    assert "class_allocation: classes" in portfolio


def test_etf_classes_are_explicit_in_operations_and_quote_refresh() -> None:
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    discovery = (STATIC / "js/features/asset-discovery.js").read_text(encoding="utf-8")
    assert 'value="BRAZILIAN_ETF">ETF Brasil' in page
    assert 'value="INTERNATIONAL_ETF">ETF Internacional' in page
    assert 'value="US_REIT">REIT' in page
    assert '"BRAZILIAN_ETF"' in discovery
    assert '"INTERNATIONAL_ETF"' in discovery
    assert '"US_REIT"' in discovery
    assert "const exact = response.candidates.find" in discovery
    assert "await applyCandidate(exact)" in discovery


def test_holdings_experience_uses_one_aggregate_projection_and_strategy_context() -> None:
    client = (STATIC / "js/api.js").read_text(encoding="utf-8")
    portfolio = (STATIC / "js/features/portfolio.js").read_text(encoding="utf-8")
    dashboard = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "/portfolio/holdings" in client
    assert '"Alvo classe"' in portfolio
    assert "#portfolio-evolution" in portfolio
    assert "Custo registrado" in dashboard
    assert "resultado econômico" in dashboard
    assert "Number(point.total_cost) + Number(point.total_result)" in portfolio
    assert "Rendimentos recebidos" in dashboard
    assert '"capital-gain": capitalGain' in portfolio
    assert "afterLayout" in portfolio
    assert "ResizeObserver" in portfolio
    assert "responsiveDateAxis(equityChart, target)" in portfolio
    assert "chart.resize()" in portfolio
    assert "Pontos de atenção" in dashboard


def test_fixed_income_holdings_keep_distinct_contracts_separate() -> None:
    portfolio = (STATIC / "js/features/portfolio.js").read_text(encoding="utf-8")
    assert "asset.contract_key" in portfolio
    assert "contract_label" in portfolio
    assert '"Contrato", "Aplicações"' in portfolio


def test_fixed_income_form_hides_inapplicable_contract_fields() -> None:
    operations = (STATIC / "js/features/operations.js").read_text(encoding="utf-8")
    styles = (STATIC / "css/app.css").read_text(encoding="utf-8")
    assert 'input.closest("label").hidden' in operations
    assert "indexerLabel.hidden = false" in operations
    assert 'value="" selected disabled>Selecione o indexador' in operations
    assert "input.previousElementSibling.hidden = hide" in operations
    assert "#fixed-income-details { display: grid" in styles
    assert "#fixed-income-details > label[hidden]" in styles


def test_pension_form_uses_progressive_disclosure_without_a_manual_identifier() -> None:
    operations = (STATIC / "js/features/operations.js").read_text(encoding="utf-8")
    assert 'value="ASSOCIATION">Por associação ou entidade' in operations
    assert 'value="UNKNOWN">Não sei' in operations
    assert 'value="OTHER">Outro' in operations
    assert '["EMPLOYER", "ASSOCIATION"].includes(value("#pension-origin"))' in operations
    assert 'input.closest("[hidden]") !== null' in operations


def test_critical_submits_are_bound_to_the_modular_api_client() -> None:
    operations = (STATIC / "js/features/operations.js").read_text(encoding="utf-8")
    strategy = (STATIC / "js/features/strategy.js").read_text(encoding="utf-8")
    assert '"#trade-form"' in operations
    assert "portfolioApi.createTrade" in operations
    assert "portfolioApi.dividend" in operations
    assert "portfolioApi.externalFlow" in operations
    assert "strategy-workspace" in strategy
    assert "portfolioApi.holdings" in strategy
    assert "portfolioApi.allocationAnalysis" in strategy
    assert "portfolioApi.allocationPolicy" in strategy
    assert "portfolioApi.assetAllocationPolicy" in strategy
    assert "data-save-strategy" in strategy
    app = (STATIC / "js/app.js").read_text(encoding="utf-8")
    assert 'from "./features/strategy.js?v=' in app


def test_income_entry_does_not_request_an_automatic_market_price() -> None:
    discovery = (STATIC / "js/features/asset-discovery.js").read_text(encoding="utf-8")
    assert 'if (eventType?.value !== "BUY") return;' in discovery
    assert "receiving income is not a price-update event" in discovery


def test_operations_history_uses_independent_tabs_and_monthly_timeline() -> None:
    client = (STATIC / "js/api.js").read_text(encoding="utf-8")
    operations = (STATIC / "js/features/operations.js").read_text(encoding="utf-8")
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "operationsHistory" in client
    assert "history-filters" in operations
    assert 'data-operations-tab="ALL"' in page
    assert 'data-operations-tab="MOVEMENTS"' in page
    assert 'data-operations-tab="INCOME"' in page
    assert "operationsTabs.get(activeOperationsTab)" in operations
    assert "requestId !== state.requestId" in operations
    assert "renderTimeline(events)" in operations
    assert "timeline-month" in operations
    assert "timeline-day" in operations
    assert "showRecurring" not in operations


def test_operation_modal_is_global_reuses_existing_write_endpoints_and_supports_prefill() -> None:
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    app = (STATIC / "js/app.js").read_text(encoding="utf-8")
    operations = (STATIC / "js/features/operations.js").read_text(encoding="utf-8")
    portfolio = (STATIC / "js/features/portfolio.js").read_text(encoding="utf-8")
    assert 'id="header-new-operation"' in page
    assert 'id="operation-modal"' in page
    assert 'id="trade-form"' in page
    assert 'id="recurrence-modal"' in page
    assert "bindOperations();" in app
    assert "data-open-operation" in portfolio
    assert 'window.dispatchEvent(new CustomEvent("income:open-operation"' in portfolio
    assert "portfolioApi.createTrade(payload)" in operations
    assert "portfolioApi.createFixedIncome" in operations
    assert "portfolioApi.createRecurringRule" in operations


def test_investor_journey_navigation_exposes_all_product_areas() -> None:
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    for area in (
        "minha-carteira",
        "entender",
        "estrategia",
        "risco-exposicao",
        "simular",
        "configuracoes",
    ):
        assert f'data-page="{area}"' in page
        assert f'href="#{area}"' in page


def test_navigation_keeps_the_selected_area_in_the_url_hash() -> None:
    navigation = (STATIC / "js/features/navigation.js").read_text(encoding="utf-8")
    assert "window.location.hash" in navigation
    assert "hashchange" in navigation
    assert "aria-current" in navigation


def test_cockpit_and_findings_use_backend_comparison_and_deep_links() -> None:
    client = (STATIC / "js/api.js").read_text(encoding="utf-8")
    portfolio = (STATIC / "js/features/portfolio.js").read_text(encoding="utf-8")
    intelligence = (STATIC / "js/features/intelligence.js").read_text(encoding="utf-8")
    assert "benchmark-comparison" in client
    assert "renderPerformanceSummary" in portfolio
    assert "Indisponível" in portfolio
    assert '"risco-exposicao"' in intelligence
    assert '"estrategia"' in intelligence


def test_intelligence_is_exposed_by_the_global_attention_center() -> None:
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    center = (STATIC / "js/features/attention-center.js").read_text(encoding="utf-8")
    assert 'data-page="pontos-atencao"' not in page
    assert 'href="#pontos-atencao"' not in page
    assert 'id="attention-center-trigger"' in page
    assert "should_surface" in center
    assert "PORTFOLIO_DRIFT" in center
    assert "COUNTRY_CONCENTRATION" in center
    assert "INCOMPLETE_RISK_COVERAGE" in center
    assert 'category !== "DATA_QUALITY"' in center
    assert 'window.location.hash === "#pontos-atencao"' in center


def test_ux_helpers_cover_feedback_validation_and_dangerous_confirmation() -> None:
    ui = (STATIC / "js/shared/ui.js").read_text(encoding="utf-8")
    operations = (STATIC / "js/features/operations.js").read_text(encoding="utf-8")
    assert "friendlyError" in ui
    assert "withProcessing" in ui
    assert "confirmDangerousAction" in ui
    assert "validateForm" in operations
    assert "confirmDangerousAction" in operations


def test_settings_can_force_a_manual_quote_refresh():
    page = (STATIC / "index.html").read_text(encoding="utf-8")
    app = (STATIC / "js/app.js").read_text(encoding="utf-8")
    feature = (STATIC / "js/features/market-price-settings.js").read_text(encoding="utf-8")
    assert 'id="settings-refresh-prices"' in page
    assert "bindMarketPriceSettings" in app
    assert "portfolioApi.refreshPrices()" in feature
    assert "Atualizar cotações agora" in page
    assert 'id="settings-refresh-price-history"' in page
    assert "portfolioApi.marketPriceRefreshRuns(20)" in feature
    api = (STATIC / "js/api.js").read_text(encoding="utf-8")
    assert "/market-prices/refresh-runs?limit=" in api


def test_portfolio_history_chart_uses_economic_result_and_preserves_negative_returns() -> None:
    portfolio = (STATIC / "js/features/portfolio.js").read_text(encoding="utf-8")
    operations = (STATIC / "js/features/operations.js").read_text(encoding="utf-8")
    assert 'id="portfolio-history-period"' in portfolio
    assert 'id="portfolio-history-class"' in portfolio
    assert (
        'event.target.matches("#portfolio-history-period, #portfolio-history-class")' in portfolio
    )
    assert "Number(point.total_cost) + Number(point.total_result)" in portfolio
    assert 'type: "line"' in portfolio
    assert "Math.max(Number(point.total_result)" not in portfolio
    assert "data: points.map(point => Number(point.capital_gain))" not in portfolio
    assert "item.market_value !== null && Number(item.market_value) > 0" in portfolio
    assert "Number(item.market_value) / total" in portfolio
    assert "value: Number(group.market_value)" in portfolio
    assert "id='history-period'" in operations


def test_financial_methodology_is_centralized_and_deep_linkable() -> None:
    concepts = (STATIC / "js/shared/financial-concepts.js").read_text(encoding="utf-8-sig")
    methodology = (STATIC / "js/features/methodology.js").read_text(encoding="utf-8-sig")
    navigation = (STATIC / "js/features/navigation.js").read_text(encoding="utf-8-sig")
    portfolio = (STATIC / "js/features/portfolio.js").read_text(encoding="utf-8-sig")
    page = (STATIC / "index.html").read_text(encoding="utf-8-sig")
    assert "Rentabilidade TWR" in concepts
    assert "Aportes e retiradas" in concepts or "aportes e retiradas" in concepts
    assert "setupMethodologyPage" in methodology
    assert "#ajuda-metodologia/${escapeConceptHtml(section.id)}" in methodology
    assert 'split("/")[0]' in navigation
    assert "financialConcepts.returnTooltip" in portfolio
    assert '"Variação"' in portfolio
    assert "performance-methodology-copy" in page
    assert "Ajuda e metodologia" in methodology
