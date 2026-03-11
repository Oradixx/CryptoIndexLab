from fastapi import Request

from src.services.index_service import IndexService


def get_index_service(request: Request) -> IndexService:
    return request.app.state.index_service
