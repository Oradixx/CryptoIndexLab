from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.core.config import settings
from src.db.init_db import init_db
from src.routes.assets import router as assets_router
from src.routes.health import router as health_router
from src.routes.indexes import router as indexes_router
from src.routes.market import router as market_router
from src.services.market_data import MarketDataService


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Business service for custom crypto index management in CryptoIndexLab.",
        lifespan=lifespan,
    )

    app.state.market_data_service = MarketDataService()

    app.include_router(health_router)
    app.include_router(assets_router)
    app.include_router(indexes_router)
    app.include_router(market_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.port, reload=False)
