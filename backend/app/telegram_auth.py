import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class TelegramAuthError(Exception):
    pass


def validate_init_data(init_data: str, bot_token: str, max_age: int = 86400) -> dict:
    """Validate Telegram WebApp initData per the official algorithm.

    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not bot_token:
        raise TelegramAuthError("bot token is not configured")
    if not init_data:
        raise TelegramAuthError("empty init data")

    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as exc:
        raise TelegramAuthError("malformed init data") from exc

    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise TelegramAuthError("missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise TelegramAuthError("invalid hash")

    auth_date = int(parsed.get("auth_date", "0"))
    if max_age and (time.time() - auth_date) > max_age:
        raise TelegramAuthError("init data expired")

    user = None
    if "user" in parsed:
        try:
            user = json.loads(parsed["user"])
        except json.JSONDecodeError as exc:
            raise TelegramAuthError("malformed user field") from exc

    return {"user": user, "auth_date": auth_date, "raw": parsed}
