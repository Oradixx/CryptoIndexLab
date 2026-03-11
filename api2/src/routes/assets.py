from fastapi import APIRouter, Depends

from src.core.dependencies import get_index_service
from src.schemas.assets import AvailableAssetsListResponse
from src.services.index_service import IndexService

router = APIRouter(tags=["assets"])


@router.get("/assets/available", response_model=AvailableAssetsListResponse)
def list_available_assets(
    index_service: IndexService = Depends(get_index_service),
) -> AvailableAssetsListResponse:
    assets = index_service.list_available_assets()
    return AvailableAssetsListResponse(assets=assets, total=len(assets))
