"""
FastAPI application factory.

Creates and configures the application instance with:
- CORS middleware (configured from settings)
- Health check endpoint
- API v1 router(s)

Usage:
    # Run with uvicorn:
    uvicorn app.main:app --reload

    # Or via Docker:
    docker compose up
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.config import settings


def create_app() -> FastAPI:
    """
    Application factory pattern.

    Why a factory function instead of a module-level `app = FastAPI()`?
    - Testability: tests can call create_app() with different configs.
    - Avoids side effects at import time.
    - Clean separation of configuration from instantiation.
    """

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Production-ready Digital Wallet + Ledger System with double-entry accounting.",
        openapi_url="/api/v1/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ---- CORS Middleware ----
    # Must be added before routes. Controls which frontend origins
    # can make API requests. Misconfigured CORS = blocked requests.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # allow_credentials=True: allows cookies/auth headers.
        # allow_methods=["*"]: allows GET, POST, PUT, DELETE, etc.
        # allow_headers=["*"]: allows Authorization, Content-Type, etc.
    )

    # ---- Health Check ----
    @app.get("/health", tags=["Health"])
    async def health_check():
        """
        Basic health check — returns 200 if the app is running.
        Used by Docker HEALTHCHECK and load balancers.
        """
        return {"status": "healthy"}

    # ---- API v1 Routers ----
    app.include_router(
        auth_router,
        prefix="/api/v1/auth",
        tags=["Auth"],
    )

    from app.wallet.routes import router as wallet_router
    app.include_router(
        wallet_router,
        prefix="/api/v1/wallets",
        tags=["Wallets"],
    )

    from app.transfers.routes import router as transfers_router
    app.include_router(
        transfers_router,
        prefix="/api/v1/transfers",
        tags=["Transfers"],
    )

    from app.merchant.routes import router as merchant_router
    app.include_router(
        merchant_router,
        prefix="/api/v1/merchant",
        tags=["Merchant"],
    )

    return app


app = create_app()
