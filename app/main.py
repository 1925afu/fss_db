from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api.v1.api import api_router

# FastAPI 앱 생성
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="금융위원회 의결서 데이터 분석 및 자연어 쿼리 시스템",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS 설정 - OPTIONS 요청 문제 해결
# allow_credentials=True와 allow_origins=["*"]는 함께 사용할 수 없음
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # 프론트엔드 오리진 명시
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
    expose_headers=["*"],
    max_age=3600  # preflight 캐시 시간 설정
)

# API 라우터 등록
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    init_db()
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 서버가 시작되었습니다! (V2 API 활성화)")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    print("👋 서버가 종료되었습니다.")


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": f"환영합니다! {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )