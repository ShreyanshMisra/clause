"""Password hashing and stateless session tokens — stdlib only, no deps.

A login verifies the password once and issues an HMAC-signed token carrying the
email + an expiry. Case-scoped endpoints trust that token instead of a raw
(spoofable) email header. The token is stateless, so there's no session table
to manage; keep the TTL modest since individual tokens can't be revoked early.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

_ITERATIONS = 200_000
_TOKEN_TTL = 7 * 24 * 3600  # 1 week

# Sign tokens with SECRET_KEY. If it's unset we fall back to a *random*
# per-process secret (never a hardcoded one), so tokens can never be forged
# from a value that lives in the source. The tradeoff is that tokens don't
# survive a restart when SECRET_KEY isn't configured — hence the warning.
_env_secret = os.environ.get("SECRET_KEY")
if _env_secret:
    _SECRET = _env_secret.encode()
else:
    import logging
    _SECRET = secrets.token_bytes(32)
    logging.getLogger(__name__).warning(
        "SECRET_KEY not set — using an ephemeral random secret; sessions won't "
        "survive a restart. Set SECRET_KEY in production."
    )


# ── Passwords ──────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


# ── Session tokens ─────────────────────────────────────────────────────────
def _sign(body: str) -> str:
    return hmac.new(_SECRET, body.encode(), hashlib.sha256).hexdigest()[:32]


def sign_token(email: str, ttl: int = _TOKEN_TTL) -> str:
    payload = {"e": email, "x": time.time() + ttl}
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    return f"{body}.{_sign(body)}"


def email_from_token(header: str | None) -> str | None:
    """Return the email a valid, unexpired token attests to, else None.
    Accepts either a bare token or an 'Authorization: Bearer <token>' value."""
    if not header:
        return None
    token = header[7:] if header[:7].lower() == "bearer " else header
    try:
        body, sig = token.split(".", 1)
        if not hmac.compare_digest(sig, _sign(body)):
            return None
        data = json.loads(base64.urlsafe_b64decode(body))
        return data["e"] if data["x"] > time.time() else None
    except Exception:
        return None
