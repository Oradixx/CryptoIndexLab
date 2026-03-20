from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import settings
from src.core.security import SimpleTokenManager
from src.db.init_db import init_db
from src.routes.auth import router as auth_router
from src.routes.health import router as health_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="User management and authentication service for CryptoIndexLab.",
        lifespan=lifespan,
        root_path="/api1",
    )

    app.state.token_manager = SimpleTokenManager(
        secret_key=settings.token_secret,
        ttl_seconds=settings.token_ttl_seconds,
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.port, reload=False)
