from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from income_analytics.domain.wealth_details import PensionPlanDetails, RealEstateDetails


def test_pension_normalizes_valid_institution_cnpj() -> None:
    details = PensionPlanDetails(
        asset_id=uuid4(), pension_type="PGBL", institution="Banco X",
        institution_cnpj="12.345.678/0001-95", plan_name="Plano X",
        tax_regime="DESCONHECIDO", start_date=date(2024, 1, 1),
        reported_balance=Decimal("80000"), reported_balance_date=date(2026, 8, 28),
    )
    assert details.institution_cnpj == "12345678000195"


def test_pension_rejects_invalid_cnpj() -> None:
    with pytest.raises(ValueError, match="valid CNPJ"):
        PensionPlanDetails(
            asset_id=uuid4(), pension_type="VGBL", institution="Banco X",
            institution_cnpj="12345678000190", plan_name="Plano X",
            tax_regime="PROGRESSIVO", start_date=date(2024, 1, 1),
            reported_balance=Decimal("0"), reported_balance_date=date(2024, 1, 1),
        )


def pension_details(**overrides: object) -> PensionPlanDetails:
    values: dict[str, object] = {
        "asset_id": uuid4(),
        "institution": "Administrador",
        "institution_cnpj": None,
        "plan_name": "Plano de teste",
        "tax_regime": "UNDEFINED",
        "start_date": date(2024, 1, 1),
        "reported_balance": Decimal("1000"),
        "reported_balance_date": date(2026, 8, 28),
    }
    values.update(overrides)
    return PensionPlanDetails(**values)  # type: ignore[arg-type]


def test_pension_accepts_open_pgbl_and_undefined_tax_regime() -> None:
    details = pension_details(product_type="PGBL")

    assert details.product_type == "PGBL"
    assert details.tax_regime == "UNDEFINED"


@pytest.mark.parametrize("modality", ["CD", "CV", "BD"])
def test_pension_accepts_closed_modalities(modality: str) -> None:
    details = pension_details(
        pension_system_type="CLOSED",
        closed_plan_modality=modality,
    )

    assert details.closed_plan_modality == modality
    assert details.product_type is None


def test_pension_rejects_open_plan_with_closed_modality() -> None:
    with pytest.raises(ValueError, match="closed_plan_modality"):
        pension_details(product_type="PGBL", closed_plan_modality="CD")


def test_pension_rejects_closed_plan_with_open_product() -> None:
    with pytest.raises(ValueError, match="product_type"):
        pension_details(
            pension_system_type="CLOSED",
            product_type="PGBL",
            closed_plan_modality="CD",
        )


def test_pension_accepts_employer_match_above_one_hundred_percent() -> None:
    details = pension_details(
        ownership_origin="EMPLOYER",
        sponsor_name="Empresa patrocinadora",
        employer_match_enabled=True,
        employer_match_rate=Decimal("150"),
        vesting_enabled=True,
        current_vested_percentage=Decimal("50"),
    )

    assert details.employer_match_rate == Decimal("150")


def test_pension_rejects_vesting_outside_the_valid_range() -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        pension_details(current_vested_percentage=Decimal("101"))


def test_pension_requires_consistent_explicit_balance_composition() -> None:
    with pytest.raises(ValueError, match="must equal"):
        pension_details(
            participant_balance=Decimal("700"),
            sponsor_balance=Decimal("200"),
        )


def test_real_estate_uses_only_owned_share_for_portfolio_value() -> None:
    details = RealEstateDetails(
        asset_id=uuid4(), property_type="APARTMENT", description="Apartamento",
        cep="13184-000", country="BR", city="Hortolândia", state="SP",
        acquisition_date=date(2022, 6, 1), acquisition_value=Decimal("500000"),
        ownership_percentage=Decimal("50"), current_manual_value=Decimal("600000"),
        valuation_date=date(2026, 8, 28),
    )
    assert details.cep == "13184000"
    assert details.portfolio_value == Decimal("300000")
