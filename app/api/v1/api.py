from fastapi import APIRouter
from app.api.v1.endpoints import decisions, search

# API 라우터 생성
api_router = APIRouter()

# 각 엔드포인트 라우터 등록
api_router.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
api_router.include_router(search.router, prefix="/search", tags=["search"])