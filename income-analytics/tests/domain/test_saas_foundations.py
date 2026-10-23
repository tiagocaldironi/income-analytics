"""Pure policy tests: no identity provider or HTTP authorization is implied."""

from uuid import uuid4

import pytest

from income_analytics.domain.saas import (
    Capability,
    Plan,
    StaffRole,
    SubscriptionStatus,
    User,
    allows_capability,
    effective_plan,
    owns_portfolio,
)


def test_two_users_four_portfolios_deny_by_default():
    a, b = User(uuid4()), User(uuid4())
    portfolios = {uuid4(): owner for owner in (a.id, a.id, b.id, b.id)}
    for owner in portfolios.values():
        assert owns_portfolio(a, owner) == (owner == a.id)
        assert owns_portfolio(b, owner) == (owner == b.id)
        assert not owns_portfolio(None, owner)
        assert not owns_portfolio(User(owner, active=False), owner)
    assert not owns_portfolio(a, None)
    for _role in StaffRole:
        # Staff capabilities never replace the owner predicate.
        assert not owns_portfolio(a, b.id)


@pytest.mark.parametrize("plan", list(Plan))
@pytest.mark.parametrize("capability", list(Capability))
def test_manual_features_are_free_and_automation_stays_closed(plan, capability):
    assert allows_capability(capability, plan) == (
        capability
        in {
            Capability.MANUAL_PORTFOLIOS,
            Capability.ANALYTICS,
            Capability.STRATEGIES,
            Capability.SIMULATIONS,
            Capability.REPORTS,
        }
    )


def test_default_and_lapsed_grants_fall_back_to_free():
    assert effective_plan() == Plan.FREE
    for status in SubscriptionStatus:
        assert effective_plan(Plan.FREE, status) == Plan.FREE
        expected = (
            Plan.PRO
            if status
            in (
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING,
            )
            else Plan.FREE
        )
        assert effective_plan(Plan.PRO, status) == expected
