"""Exception for invalid monetary values."""

from .domain_exception import DomainError


class InvalidMoneyError(DomainError):
    """Raised when a monetary value violates a domain rule."""
