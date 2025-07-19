from fastapi import APIRouter
from app.api.v1.endpoints import decisions, search, laws, actions

# API 라우터 생성
api_router = APIRouter()

# 각 엔드포인트 라우터 등록
api_router.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(laws.router, prefix="/laws", tags=["laws"])
api_router.include_router(actions.router, prefix="/actions", tags=["actions"])