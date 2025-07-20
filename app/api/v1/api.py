from fastapi import APIRouter
from app.api.v1.endpoints import decisions_v2, search_v2

# API 라우터 생성
api_router = APIRouter()

# V1 엔드포인트는 더 이상 사용하지 않음 (V1 서비스 파일들이 아카이브로 이동됨)
# 필요시 V1 엔드포인트를 복구하려면 archive/old_services에서 파일들을 복원

# V2 엔드포인트만 활성화
api_router.include_router(decisions_v2.router, prefix="/v2/decisions", tags=["decisions_v2"])
api_router.include_router(search_v2.router, prefix="/v2/search", tags=["search_v2"])