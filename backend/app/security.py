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
# Set SECRET_KEY in the environment for production; the dev fallback keeps local
# runs working but means tokens are forgeable if the default is left in place.
_SECRET = os.environ.get("SECRET_KEY", "dev-insecure-secret-change-me").encode()
_TOKEN_TTL = 7 * 24 * 3600  # 1 week


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
