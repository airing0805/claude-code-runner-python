"""认证模块"""

from app.auth.core import (
    ACCESS_TOKEN_EXPIRE_HOURS,
    authenticate_user,
    create_access_token,
    create_user,
    create_api_key,
    decode_access_token,
    delete_api_key,
    generate_api_key,
    get_api_key_by_id,
    get_user_api_keys,
    get_user_by_id,
    get_user_by_username,
    hash_password,
    revoke_api_key,
    update_user_password,
    validate_password_strength,
    verify_api_key,
    verify_password,
)
from app.auth.dependencies import (
    api_key_header,
    get_api_key_user,
    get_current_user,
    get_current_user_optional,
    oauth2_scheme,
)

__all__ = [
    # Core
    "verify_password",
    "hash_password",
    "validate_password_strength",
    "create_access_token",
    "decode_access_token",
    "get_user_by_username",
    "get_user_by_id",
    "create_user",
    "authenticate_user",
    "update_user_password",
    "generate_api_key",
    "verify_api_key",
    "create_api_key",
    "get_user_api_keys",
    "get_api_key_by_id",
    "revoke_api_key",
    "delete_api_key",
    "ACCESS_TOKEN_EXPIRE_HOURS",
    # Dependencies
    "get_current_user",
    "get_current_user_optional",
    "get_api_key_user",
    "oauth2_scheme",
    "api_key_header",
]
