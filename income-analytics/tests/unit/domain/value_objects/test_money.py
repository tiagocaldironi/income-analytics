from decimal import Decimal

from income_analytics.domain.value_objects.money import Money


def test_should_create_money() -> None:
    money = Money(Decimal("100"))

    assert money.amount == Decimal("100")
