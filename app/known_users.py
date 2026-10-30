"""The demo users, their API keys and their starting limits.

Edit this file to add users or change quotas for a demo. In a real system
this data would come from a database; a plain dict keeps the demo simple.
"""

from app.models.rate_limit import RateLimitConfig
from app.models.user import ADMIN_ROLE, USER_ROLE, User
from app.settings import settings

# API key sent in the X-API-Key header  ->  the user it belongs to.
API_KEYS_TO_USERS = {
    "key-user-101": User(user_id="user_101", role=USER_ROLE),
    "key-user-102": User(user_id="user_102", role=USER_ROLE),
    "key-user-103": User(user_id="user_103", role=USER_ROLE),
    "key-user-104": User(user_id="user_104", role=USER_ROLE),
    "key-user-105": User(user_id="user_105", role=USER_ROLE),
    "key-user-106": User(user_id="user_106", role=USER_ROLE),
    "key-user-107": User(user_id="user_107", role=USER_ROLE),
    "key-user-108": User(user_id="user_108", role=USER_ROLE),
    # The admin key comes from settings so it is easy to change.
    settings.admin_api_key: User(user_id="admin", role=ADMIN_ROLE),
}

# Starting quota per user. Users missing here get the default from settings.
STARTING_LIMITS_BY_USER = {
    "user_101": RateLimitConfig(limit=5, window_seconds=60),
    "user_102": RateLimitConfig(limit=10, window_seconds=60),
    "user_104": RateLimitConfig(limit=3, window_seconds=60),
    "user_105": RateLimitConfig(limit=4, window_seconds=60),
    "user_106": RateLimitConfig(limit=5, window_seconds=60),
    "user_107": RateLimitConfig(limit=7, window_seconds=60),
    "user_108": RateLimitConfig(limit=10, window_seconds=60),
}

# Ids of normal (non-admin) users, used by analytics and config checks.
REGULAR_USER_IDS = [
    user.user_id
    for user in API_KEYS_TO_USERS.values()
    if not user.is_admin
]


def is_known_user(user_id: str) -> bool:
    """Tell whether a normal user with this id exists."""
    return user_id in REGULAR_USER_IDS
