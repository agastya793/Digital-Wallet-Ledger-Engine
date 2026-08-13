"""
Application configuration loaded from environment variables.

Uses pydantic-settings to:
1. Load values from .env file (development) or real env vars (production).
2. Validate types at startup — fail fast if config is wrong.
3. Provide typed access throughout the codebase (no string casting).

Usage:
    from app.config import settings
    print(settings.DATABASE_URL)
"""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings.

    All fields map to environment variables. Pydantic automatically:
    - Reads from .env file (via model_config)
    - Casts strings to the declared Python type
    - Raises ValidationError at startup if a required field is missing
    """

    # -----------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------
    APP_NAME: str = "digital-wallet-ledger-engine"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    # Literal type = only these 3 values are valid. Anything else → startup error.

    APP_DEBUG: bool = True
    APP_VERSION: str = "0.1.0"

    # -----------------------------------------------------------------
    # Server
    # -----------------------------------------------------------------
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # -----------------------------------------------------------------
    # Database (PostgreSQL)
    # -----------------------------------------------------------------
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/wallet_db"
    )
    # No default in production — must be explicitly set.
    # Default here is for local development convenience only.

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False
    # DB_ECHO=True logs all SQL. Useful for debugging, noisy in production.

    # -----------------------------------------------------------------
    # Authentication (JWT)
    # -----------------------------------------------------------------
    JWT_SECRET_KEY: str = "change-me-to-a-random-64-char-string-in-production"

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # -----------------------------------------------------------------
    # Redis
    # -----------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 5

    # Upstash-specific settings (used in production instead of REDIS_URL)
    UPSTASH_REDIS_REST_URL: str | None = None
    UPSTASH_REDIS_REST_TOKEN: str | None = None

    # -----------------------------------------------------------------
    # Rate Limiting
    # -----------------------------------------------------------------
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10

    # -----------------------------------------------------------------
    # Idempotency
    # -----------------------------------------------------------------
    IDEMPOTENCY_KEY_TTL_HOURS: int = 24

    # -----------------------------------------------------------------
    # CORS
    # -----------------------------------------------------------------
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://localhost:5175"
    # Stored as comma-separated string in env var, parsed into list below.

    # -----------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["console", "json"] = "console"

    # =================================================================
    # Pydantic Settings Configuration
    # =================================================================
    model_config = SettingsConfigDict(
        # ---- .env file loading ----
        env_file=".env",
        # Looks for .env in the current working directory.
        # In Docker: the WORKDIR in Dockerfile.
        # Locally: the project root.
        env_file_encoding="utf-8",
        # Explicit encoding — prevents issues on Windows.
        case_sensitive=True,
        # ENV_VAR names are case-sensitive. DATABASE_URL ≠ database_url.
        # This prevents subtle bugs from case mismatches.
        extra="ignore",
        # Ignore env vars that don't match any field.
        # Without this, a typo like DATBASE_URL would silently be ignored
        # AND raise a validation error for missing DATABASE_URL.
        # "ignore" is safer than "forbid" for real environments that have
        # many unrelated env vars (PATH, HOME, etc.)
    )

    # =================================================================
    # Computed Properties
    # =================================================================
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.APP_ENV == "development"

    @property
    def use_upstash(self) -> bool:
        """Check if Upstash Redis should be used instead of standard Redis."""
        return (
            self.UPSTASH_REDIS_REST_URL is not None
            and self.UPSTASH_REDIS_REST_TOKEN is not None
        )

    # =================================================================
    # Validators
    # =================================================================
    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """
        Warn if JWT secret is the default value.

        In production, using the default secret means anyone can forge
        valid JWT tokens — effectively bypassing all authentication.
        """
        if v == "change-me-to-a-random-64-char-string-in-production":
            import warnings

            warnings.warn(
                "JWT_SECRET_KEY is using the default value. "
                "Generate a secure key with: "
                'python -c "import secrets; print(secrets.token_urlsafe(64))"',
                UserWarning,
                stacklevel=2,
            )
        return v

    @field_validator("DB_POOL_SIZE")
    @classmethod
    def validate_pool_size(cls, v: int) -> int:
        """Ensure pool size is reasonable."""
        if v < 1:
            msg = "DB_POOL_SIZE must be at least 1"
            raise ValueError(msg)
        if v > 50:
            msg = "DB_POOL_SIZE > 50 is likely a misconfiguration"
            raise ValueError(msg)
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Create and cache a Settings instance.

    Why lru_cache?
    - Settings are read from env vars / .env file — this is I/O.
    - We only need to do it once. All subsequent calls return the cached instance.
    - This is the standard pattern recommended by FastAPI docs.

    Why a function and not a module-level variable?
    - Testability. In tests, you can override this with dependency injection:
        app.dependency_overrides[get_settings] = lambda: TestSettings(...)
    - A module-level `settings = Settings()` would be created at import time,
      making it impossible to override for tests without monkey-patching.
    """
    return Settings()


# -------------------------------------------------------------------------
# Convenience alias — use this for quick access outside of FastAPI routes.
# Inside routes, prefer dependency injection via get_settings() for testability.
# -------------------------------------------------------------------------
settings = get_settings()
