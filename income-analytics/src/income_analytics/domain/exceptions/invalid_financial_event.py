"""Exception for invalid financial events."""

from .domain_exception import DomainError


class InvalidFinancialEventError(DomainError):
    """Raised when a financial event violates a domain rule."""
