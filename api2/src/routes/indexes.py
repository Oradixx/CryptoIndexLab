from fastapi import APIRouter, Depends, HTTPException, status

from src.core.dependencies import get_index_service
from src.core.exceptions import DomainValidationError
from src.models.index import CryptoIndex
from src.schemas.indexes import CreateIndexRequest, IndexListResponse, IndexResponse
from src.services.index_service import IndexService

router = APIRouter(tags=["indexes"])


def _to_index_response(index: CryptoIndex) -> IndexResponse:
    total_weight = round(sum(asset.weight for asset in index.assets), 4)
    return IndexResponse(
        id=index.id,
        name=index.name,
        assets=index.assets,
        total_weight=total_weight,
        owner_user_id=index.owner_user_id,
        created_at=index.created_at,
    )


@router.get("/indexes", response_model=IndexListResponse)
def list_indexes(
    index_service: IndexService = Depends(get_index_service),
) -> IndexListResponse:
    indexes = index_service.list_indexes()
    response_items = [_to_index_response(index_obj) for index_obj in indexes]
    return IndexListResponse(indexes=response_items, total=len(response_items))


@router.get("/indexes/{index_id}", response_model=IndexResponse)
def get_index(
    index_id: str,
    index_service: IndexService = Depends(get_index_service),
) -> IndexResponse:
    index_obj = index_service.get_index(index_id)
    if not index_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Index not found.",
        )

    return _to_index_response(index_obj)


@router.post("/indexes", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
def create_index(
    payload: CreateIndexRequest,
    index_service: IndexService = Depends(get_index_service),
) -> IndexResponse:
    try:
        created_index = index_service.create_index(
            name=payload.name,
            assets=[(asset.symbol, asset.weight) for asset in payload.assets],
            owner_user_id=payload.owner_user_id,
        )
    except DomainValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _to_index_response(created_index)
