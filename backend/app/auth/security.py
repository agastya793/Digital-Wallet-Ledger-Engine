"""
Security utilities — password hashing and JWT token management.

This module is the cryptographic foundation of the auth system.
It handles three concerns:

1. **Password Hashing** (bcrypt via passlib)
   - hash_password():   plaintext → bcrypt hash (for storage)
   - verify_password():  plaintext + hash → bool (for login)

2. **JWT Access Tokens** (pyjwt)
   - create_access_token():  user data → signed JWT string
   - decode_access_token():  JWT string → payload dict (or raises)

3. **Opaque Refresh Tokens** (secrets + hashlib)
   - generate_refresh_token():  → random URL-safe string
   - hash_refresh_token():      token → SHA-256 hex digest (for DB storage)

Design decisions:
- We NEVER store plaintext refresh tokens in the database.
  Only the SHA-256 hash is stored. If the DB leaks, the hashes
  are useless without the original token.
- Access tokens are stateless JWTs (verified by signature, not DB lookup).
  Refresh tokens are stateful (verified against a DB record).
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

# =============================================================================
# Password Hashing
# =============================================================================
# CryptContext manages the hashing scheme. If we ever migrate from bcrypt
# to argon2, we add it to `schemes` and passlib handles the transition
# automatically (old hashes still verify, new hashes use the new scheme).
# =============================================================================
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    # "auto" = if we add a new scheme later, bcrypt hashes are auto-deprecated
    # and re-hashed on next successful login. Zero-downtime migration.
)


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Bcrypt automatically:
    - Generates a random salt (16 bytes)
    - Embeds the salt in the hash string
    - Applies the cost factor (default 12 = ~250ms per hash)

    The cost factor makes brute-force attacks impractical:
    at 250ms/hash, trying 1 billion passwords takes ~8 years.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.

    Returns True if the password matches, False otherwise.
    Constant-time comparison prevents timing attacks.
    """
    return pwd_context.verify(plain_password, hashed_password)


# =============================================================================
# JWT Access Tokens
# =============================================================================
# Access tokens are short-lived (15 min by default) and stateless.
# The server never stores them — validity is determined purely by
# signature verification and expiration time.
#
# Payload structure:
#   {
#     "sub": "<user_uuid>",     ← subject (who this token is for)
#     "role": "user|admin",     ← authorization level
#     "exp": 1234567890,        ← expiration (Unix timestamp)
#     "iat": 1234567890,        ← issued at (Unix timestamp)
#     "type": "access"          ← token type (distinguishes from refresh)
#   }
# =============================================================================


def create_access_token(
    subject: str,
    role: str = "user",
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: The user identifier (UUID as string). Goes into "sub" claim.
        role: The user's role for RBAC. Goes into "role" claim.
        expires_delta: Custom expiration. Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        Encoded JWT string.
    """
    now = datetime.now(timezone.utc)

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": subject,
        "role": role,
        "exp": now + expires_delta,
        "iat": now,
        "type": "access",
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.

    Checks:
    1. Signature is valid (not tampered with).
    2. Token has not expired (exp > now).
    3. Token was issued at a valid time (iat).

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidTokenError: Token is malformed or signature is invalid.

    Returns:
        The decoded payload dictionary.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


# =============================================================================
# Opaque Refresh Tokens
# =============================================================================
# Refresh tokens are NOT JWTs. They are random strings that map to a
# database record. This gives us:
# - Immediate revocation (set is_revoked=True in DB)
# - Token rotation (issue new token, revoke old one)
# - Audit trail (DB records show when tokens were issued/used/revoked)
#
# Flow:
# 1. generate_refresh_token() → "dBjftJeZ4CVP-mB92K27uhbUJU1p..."  (sent to client)
# 2. hash_refresh_token(token) → "a3f2b8c1..."                       (stored in DB)
# 3. On /refresh: client sends raw token → we hash it → look up hash in DB
# =============================================================================


def generate_refresh_token() -> str:
    """
    Generate a cryptographically secure random refresh token.

    Uses secrets.token_urlsafe(64) which produces an 86-character
    URL-safe base64 string from 64 random bytes.

    This is the raw token sent to the client. NEVER stored in the DB.
    """
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token for database storage using SHA-256.

    Why SHA-256 and not bcrypt?
    - Refresh tokens are 64 bytes of random data (high entropy).
    - Bcrypt's salt + cost factor protect LOW-entropy passwords from
      brute force. With 64 random bytes, brute force is already
      computationally impossible (2^512 possibilities).
    - SHA-256 is ~10,000x faster than bcrypt. Since we don't need
      the slowness for high-entropy tokens, we avoid the overhead.
    """
    return hashlib.sha256(token.encode()).hexdigest()
