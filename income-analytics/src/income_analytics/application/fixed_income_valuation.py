"""Deterministic contract-curve valuation for fixed-income positions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext

from income_analytics.domain.benchmark_rate import BenchmarkRate
from income_analytics.domain.enums.fixed_income import FixedIncomeIndexerType
from income_analytics.domain.fixed_income_details import FixedIncomeDetails

ACT_365F = Decimal("365")


@dataclass(frozen=True, slots=True)
class FixedIncomeValuation:
    asset_id: str
    effective_date: date
    gross_value: Decimal | None
    unavailable_reason: str | None = None


class FixedIncomeValuationEngine:
    """Values contracts with explicit conventions and explicit data gaps."""

    @staticmethod
    def value(
        details: FixedIncomeDetails,
        *,
        as_of: date,
        cdi_rates: tuple[BenchmarkRate, ...] = (),
        ipca_rates: tuple[tuple[date, Decimal], ...] = (),
        tr_rates: tuple[tuple[date, Decimal], ...] = (),
        selic_targets: tuple[tuple[date, Decimal], ...] = (),
    ) -> FixedIncomeValuation:
        if as_of < details.application_date:
            return FixedIncomeValuation(
                asset_id=str(details.asset_id), effective_date=as_of, gross_value=Decimal("0")
            )
        if as_of == details.application_date:
            return FixedIncomeValuation(
                asset_id=str(details.asset_id),
                effective_date=as_of,
                gross_value=details.principal_amount,
            )
        if details.indexer_type is FixedIncomeIndexerType.PREFIXED:
            return FixedIncomeValuationEngine._prefixed(details, as_of)
        if details.indexer_type in (
            FixedIncomeIndexerType.CDI_PERCENT,
            FixedIncomeIndexerType.CDI_PLUS,
        ):
            return FixedIncomeValuationEngine._cdi(details, as_of, cdi_rates)
        if details.indexer_type is FixedIncomeIndexerType.IPCA_PLUS:
            return FixedIncomeValuationEngine._ipca(details, as_of, ipca_rates)
        if details.indexer_type is FixedIncomeIndexerType.SAVINGS_RULE:
            return FixedIncomeValuationEngine._savings(details, as_of, tr_rates, selic_targets)
        return FixedIncomeValuation(
            asset_id=str(details.asset_id),
            effective_date=as_of,
            gross_value=None,
            unavailable_reason="Ainda não há regra automática para este indexador.",
        )

    @staticmethod
    def _savings(
        details: FixedIncomeDetails,
        as_of: date,
        tr_rates: tuple[tuple[date, Decimal], ...],
        selic_targets: tuple[tuple[date, Decimal], ...],
    ) -> FixedIncomeValuation:
        from calendar import monthrange

        value = details.principal_amount
        anniversary = details.application_date
        credited = False
        while True:
            month = anniversary.month % 12 + 1
            year = anniversary.year + (anniversary.month // 12)
            anniversary = date(year, month, min(anniversary.day, monthrange(year, month)[1]))
            if anniversary > as_of:
                break
            tr = next((rate for day, rate in reversed(tr_rates) if day <= anniversary), None)
            selic = next(
                (rate for day, rate in reversed(selic_targets) if day <= anniversary), None
            )
            if tr is None or selic is None:
                return FixedIncomeValuation(
                    asset_id=str(details.asset_id),
                    effective_date=as_of,
                    gross_value=None,
                    unavailable_reason="Faltam TR ou meta Selic para a data de aniversário.",
                )
            monthly_interest = (
                Decimal("0.005")
                if selic > Decimal("0.085")
                else ((Decimal("1") + selic) ** (Decimal("1") / Decimal("12")) - Decimal("1"))
                * Decimal("0.70")
            )
            value *= (Decimal("1") + tr) * (Decimal("1") + monthly_interest)
            credited = True
        return FixedIncomeValuation(
            asset_id=str(details.asset_id),
            effective_date=as_of,
            gross_value=value if credited else details.principal_amount,
        )

    @staticmethod
    def _prefixed(details: FixedIncomeDetails, as_of: date) -> FixedIncomeValuation:
        assert details.contracted_rate is not None
        days = Decimal((as_of - details.application_date).days)
        with localcontext() as context:
            context.prec = 28
            factor = (Decimal("1") + details.contracted_rate / Decimal("100")) ** (days / ACT_365F)
        return FixedIncomeValuation(
            asset_id=str(details.asset_id),
            effective_date=as_of,
            gross_value=details.principal_amount * factor,
        )

    @staticmethod
    def _cdi(
        details: FixedIncomeDetails, as_of: date, rates: tuple[BenchmarkRate, ...]
    ) -> FixedIncomeValuation:
        selected = tuple(
            rate
            for rate in rates
            if rate.name.upper() == "CDI"
            and details.application_date < rate.effective_date <= as_of
        )
        if not selected:
            if rates and max(rate.effective_date for rate in rates) <= details.application_date:
                return FixedIncomeValuation(
                    asset_id=str(details.asset_id),
                    effective_date=as_of,
                    gross_value=details.principal_amount,
                )
            return FixedIncomeValuation(
                asset_id=str(details.asset_id),
                effective_date=as_of,
                gross_value=None,
                unavailable_reason="Não há observações de CDI para valorizar este título.",
            )
        factor = Decimal("1")
        for rate in selected:
            daily_rate = rate.return_percentage
            if details.indexer_type in (
                FixedIncomeIndexerType.CDI_PERCENT,
                FixedIncomeIndexerType.CDI_PLUS,
            ):
                percentage = details.percentage_of_indexer
                if percentage is None:
                    # Compatibility for contracts entered before CDI + spread
                    # exposed its explicit CDI percentage in the interface.
                    percentage = Decimal("100")
                daily_rate *= percentage / Decimal("100")
            if details.indexer_type is FixedIncomeIndexerType.CDI_PLUS:
                assert details.spread is not None
                daily_rate = (Decimal("1") + daily_rate) * (
                    Decimal("1") + details.spread / Decimal("100")
                ) ** (Decimal("1") / ACT_365F) - Decimal("1")
            factor *= Decimal("1") + daily_rate
        return FixedIncomeValuation(
            asset_id=str(details.asset_id),
            effective_date=as_of,
            gross_value=details.principal_amount * factor,
        )

    @staticmethod
    def _ipca(
        details: FixedIncomeDetails,
        as_of: date,
        rates: tuple[tuple[date, Decimal], ...],
    ) -> FixedIncomeValuation:
        selected = tuple(
            rate
            for effective_date, rate in rates
            if details.application_date < effective_date <= as_of
        )
        if not selected:
            latest_index_date = (
                max(effective_date for effective_date, _ in rates) if rates else None
            )
            if latest_index_date is not None and latest_index_date <= details.application_date:
                return FixedIncomeValuation(
                    asset_id=str(details.asset_id),
                    effective_date=as_of,
                    gross_value=details.principal_amount,
                )
            return FixedIncomeValuation(
                asset_id=str(details.asset_id),
                effective_date=as_of,
                gross_value=None,
                unavailable_reason="Não há observações de IPCA para valorizar este título.",
            )
        assert details.spread is not None
        factor = Decimal("1")
        for monthly_rate in selected:
            factor *= Decimal("1") + monthly_rate
        years = Decimal((as_of - details.application_date).days) / ACT_365F
        factor *= (Decimal("1") + details.spread / Decimal("100")) ** years
        return FixedIncomeValuation(
            asset_id=str(details.asset_id),
            effective_date=as_of,
            gross_value=details.principal_amount * factor,
        )
