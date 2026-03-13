from src.routes.assets import router as assets_router
from src.routes.health import router as health_router
from src.routes.indexes import router as indexes_router
from src.routes.market import router as market_router

__all__ = ["assets_router", "health_router", "indexes_router", "market_router"]
