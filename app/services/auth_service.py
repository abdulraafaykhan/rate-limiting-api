"""Works out who is calling and whether they may do what they ask."""

from app.exceptions import AuthenticationFailed, PermissionDenied
from app.known_users import API_KEYS_TO_USERS
from app.models.user import User


def authenticate(api_key: str | None) -> User:
    """Turn an API key into a User, or raise AuthenticationFailed."""
    # No key sent, or a key we do not know: the caller is not logged in.
    if not api_key or api_key not in API_KEYS_TO_USERS:
        raise AuthenticationFailed()

    return API_KEYS_TO_USERS[api_key]


def require_admin(user: User) -> None:
    """Raise PermissionDenied unless the user is an admin."""
    # This is what stops a normal user from editing anyone's quota.
    if not user.is_admin:
        raise PermissionDenied()
