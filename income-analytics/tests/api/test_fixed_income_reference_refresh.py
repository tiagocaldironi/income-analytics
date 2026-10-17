from datetime import date

from income_analytics.api.routers.dashboard import (
    _fixed_income_benchmark,
    _refresh_fixed_income_reference_history,
)
from income_analytics.application.portfolio_session import PortfolioSession
from income_analytics.domain.enums.fixed_income import FixedIncomeIndexerType


def test_past_cdi_application_refreshes_its_historical_curve(monkeypatch) -> None:
    recorded: dict[str, object] = {}

    def refresh(self, provider, *, name, start_date, end_date):
        recorded.update(
            provider=provider,
            name=name,
            start_date=start_date,
            end_date=end_date,
        )

    monkeypatch.setattr(PortfolioSession, "refresh_benchmark", refresh)

    result = _refresh_fixed_income_reference_history(
        indexer_type=FixedIncomeIndexerType.CDI_PERCENT,
        application_date=date(2026, 1, 2),
    )

    assert result == ("CDI",)
    assert recorded["name"] == "CDI"
    assert recorded["start_date"] == date(2026, 1, 2)


def test_prefixed_application_does_not_need_external_reference_data() -> None:
    assert _refresh_fixed_income_reference_history(
        indexer_type=FixedIncomeIndexerType.PREFIXED,
        application_date=date(2026, 1, 2),
    ) == ()


def test_fixed_income_reference_mapping_only_uses_official_variable_indexes() -> None:
    assert _fixed_income_benchmark(FixedIncomeIndexerType.CDI_PLUS) == "CDI"
    assert _fixed_income_benchmark(FixedIncomeIndexerType.IPCA_PLUS) == "IPCA"
    assert _fixed_income_benchmark(FixedIncomeIndexerType.PREFIXED) is None
