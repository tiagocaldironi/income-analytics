"""Provider-neutral foundations. These policies do not authenticate HTTP requests."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    active: bool = True


class StaffRole(StrEnum):
    OPERATIONAL = "OPERATIONAL"
    FINANCIAL_REVIEWER = "FINANCIAL_REVIEWER"
    REGULATORY_REVIEWER = "REGULATORY_REVIEWER"


class Plan(StrEnum):
    FREE = "FREE"
    PRO = "PRO"


class SubscriptionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    TRIALING = "TRIALING"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"


class Capability(StrEnum):
    MANUAL_PORTFOLIOS = "MANUAL_PORTFOLIOS"
    ANALYTICS = "ANALYTICS"
    STRATEGIES = "STRATEGIES"
    SIMULATIONS = "SIMULATIONS"
    REPORTS = "REPORTS"
    BANK_CONNECTION = "BANK_CONNECTION"
    AUTOMATIC_SYNC = "AUTOMATIC_SYNC"
    RECONCILIATION = "RECONCILIATION"


def owns_portfolio(user: User | None, owner_user_id: UUID | None) -> bool:
    """Deny anonymous, inactive, unclaimed and foreign portfolios, including staff."""
    return user is not None and user.active and owner_user_id == user.id


def effective_plan(
    granted_plan: Plan | None = None,
    status: SubscriptionStatus | None = None,
) -> Plan:
    """Inputs must come from trusted server grants, never client claims."""
    if granted_plan == Plan.PRO and status in (
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.TRIALING,
    ):
        return Plan.PRO
    return Plan.FREE


def allows_capability(capability: Capability, plan: Plan = Plan.FREE) -> bool:
    """Free preserves manual features; future automation is unavailable for all plans."""
    return capability in {
        Capability.MANUAL_PORTFOLIOS,
        Capability.ANALYTICS,
        Capability.STRATEGIES,
        Capability.SIMULATIONS,
        Capability.REPORTS,
    }
