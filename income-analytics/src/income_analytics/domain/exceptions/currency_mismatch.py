"""Exception for operations involving incompatible currencies."""

from .domain_exception import DomainError


class CurrencyMismatchError(DomainError):
    """Raised when monetary values use different currencies."""
