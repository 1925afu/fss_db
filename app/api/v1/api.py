from fastapi import APIRouter
from app.api.v1.endpoints import decisions, search, laws, actions, decisions_v2, search_v2

# API 라우터 생성
api_router = APIRouter()

# 각 엔드포인트 라우터 등록
api_router.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(laws.router, prefix="/laws", tags=["laws"])
api_router.include_router(actions.router, prefix="/actions", tags=["actions"])

# V2 엔드포인트 추가 (실제로 작동하도록 수정)
api_router.include_router(decisions_v2.router, prefix="/v2/decisions", tags=["decisions_v2"])
api_router.include_router(search_v2.router, prefix="/v2/search", tags=["search_v2"])