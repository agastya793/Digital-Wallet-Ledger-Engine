"""
Merchant API key security — generation and hashing.

Merchant API keys use a distinct format: `sk_live_<random>`.
The "sk_live_" prefix makes it instantly recognizable in logs,
config files, and code reviews — you know exactly what it is
and that it's a secret that shouldn't be committed to git.

This follows the convention used by Stripe, Twilio, and other
payment APIs.

Storage:
    The raw API key is returned to the merchant exactly ONCE at
    registration. Only the SHA-256 hash is stored in the database.
    If the merchant loses their key, they must regenerate (future feature).

Why SHA-256 and not bcrypt?
    Same reasoning as refresh tokens in auth/security.py:
    API keys are high-entropy (64 random bytes). Bcrypt's slowness
    protects LOW-entropy passwords from brute force. With 64 bytes
    of randomness, brute force is already computationally impossible.
    SHA-256 is ~10,000x faster — appropriate for high-entropy secrets.
"""

import hashlib
import secrets


def generate_api_key() -> str:
    """
    Generate a secure merchant API key.

    Format: sk_live_<64 random URL-safe chars>
    Example: sk_live_dBjftJeZ4CVP-mB92K27uhbUJU1p1r_G...

    The "sk_" prefix = "secret key".
    The "live_" segment = production key (vs "test_" for sandbox).
    """
    random_part = secrets.token_urlsafe(48)
    return f"sk_live_{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for database storage using SHA-256.

    The raw key is never stored. On each request, the incoming
    X-API-Key header is hashed and compared against stored hashes.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()
