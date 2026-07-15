"""Exception for invalid quantities."""

from .domain_exception import DomainError


class InvalidQuantityError(DomainError):
    """Raised when a quantity violates a domain rule."""
