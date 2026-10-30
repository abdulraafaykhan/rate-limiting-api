"""The User model: who is calling the API."""

from dataclasses import dataclass

# The two roles in the system.
USER_ROLE = "user"
ADMIN_ROLE = "admin"


@dataclass(frozen=True)
class User:
    """An authenticated caller."""

    user_id: str
    role: str

    @property
    def is_admin(self) -> bool:
        """True when this user may use admin-only endpoints."""
        return self.role == ADMIN_ROLE
