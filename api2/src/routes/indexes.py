from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.core.dependencies import (
    get_current_user_id,
    get_index_performance_service,
    get_index_service,
)
from src.core.exceptions import (
    DomainValidationError,
    ForbiddenIndexAccessError,
    InsufficientHistoricalDataError,
    InvalidIndexCompositionError,
    MalformedMarketDataResponseError,
    UnsupportedSymbolError,
    UpstreamMarketDataError,
    UpstreamMarketDataTimeoutError,
)
from src.models.index import CryptoIndex
from src.schemas.indexes import (
    CreateIndexRequest,
    IndexAssetResponse,
    IndexListResponse,
    IndexResponse,
    UpdateIndexRequest,
)
from src.schemas.performance import IndexPerformanceResponse
from src.services.index_performance import IndexPerformanceService
from src.services.index_service import IndexService

router = APIRouter(tags=["indexes"])


def _to_index_response(index: CryptoIndex, index_service: IndexService) -> IndexResponse:
    total_weight = round(sum(asset.weight for asset in index.assets), 4)
    response_assets = [
        IndexAssetResponse(
            symbol=asset.symbol,
            name=index_service.resolve_asset_name(asset.symbol),
            weight=asset.weight,
        )
        for asset in index.assets
    ]
    return IndexResponse(
        id=index.id,
        name=index.name,
        assets=response_assets,
        total_weight=total_weight,
        user_id=index.user_id,
        created_at=index.created_at,
    )


@router.get("/indexes", response_model=IndexListResponse)
def list_indexes(
    current_user_id: str = Depends(get_current_user_id),
    index_service: IndexService = Depends(get_index_service),
) -> IndexListResponse:
    indexes = index_service.list_indexes(user_id=current_user_id)
    response_items = [_to_index_response(index_obj, index_service) for index_obj in indexes]
    return IndexListResponse(indexes=response_items, total=len(response_items))


@router.get("/indexes/{index_id}", response_model=IndexResponse)
def get_index(
    index_id: str,
    current_user_id: str = Depends(get_current_user_id),
    index_service: IndexService = Depends(get_index_service),
) -> IndexResponse:
    index_obj = index_service.get_index(index_id=index_id, user_id=current_user_id)
    if not index_obj:
        if index_service.index_exists(index_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this index.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found.",
        )

    return _to_index_response(index_obj, index_service)


@router.get("/indexes/{index_id}/performance", response_model=IndexPerformanceResponse)
def get_index_performance(
    index_id: str,
    current_user_id: str = Depends(get_current_user_id),
    index_performance_service: IndexPerformanceService = Depends(get_index_performance_service),
) -> IndexPerformanceResponse:
    try:
        performance = index_performance_service.calculate_index_performance(
            index_id=index_id,
            user_id=current_user_id,
        )
    except ForbiddenIndexAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (InvalidIndexCompositionError, InsufficientHistoricalDataError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UnsupportedSymbolError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UpstreamMarketDataTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    except (UpstreamMarketDataError, MalformedMarketDataResponseError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if not performance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found.",
        )

    return performance


@router.post("/indexes", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
def create_index(
    payload: CreateIndexRequest,
    current_user_id: str = Depends(get_current_user_id),
    index_service: IndexService = Depends(get_index_service),
) -> IndexResponse:
    try:
        created_index = index_service.create_index(
            name=payload.name,
            assets=[(asset.symbol, asset.weight) for asset in payload.assets],
            user_id=current_user_id,
        )
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _to_index_response(created_index, index_service)


@router.put("/indexes/{index_id}", response_model=IndexResponse)
def update_index(
    index_id: str,
    payload: UpdateIndexRequest,
    current_user_id: str = Depends(get_current_user_id),
    index_service: IndexService = Depends(get_index_service),
) -> IndexResponse:
    try:
        updated_index = index_service.update_index(
            index_id=index_id,
            name=payload.name,
            assets=[(asset.symbol, asset.weight) for asset in payload.assets],
            user_id=current_user_id,
        )
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not updated_index:
        if index_service.index_exists(index_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this index.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found.",
        )

    return _to_index_response(updated_index, index_service)


@router.delete("/indexes/{index_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_index(
    index_id: str,
    current_user_id: str = Depends(get_current_user_id),
    index_service: IndexService = Depends(get_index_service),
) -> Response:
    deleted = index_service.delete_index(index_id=index_id, user_id=current_user_id)
    if not deleted:
        if index_service.index_exists(index_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this index.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
