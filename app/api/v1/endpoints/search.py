from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.services.search_service import SearchService

router = APIRouter()


class NLQueryRequest(BaseModel):
    """자연어 쿼리 요청 모델"""
    query: str
    limit: Optional[int] = 50


class TextSearchRequest(BaseModel):
    """텍스트 검색 요청 모델"""
    text: str
    limit: Optional[int] = 50


@router.post("/nl2sql", summary="자연어 쿼리 검색")
async def natural_language_search(
    request: NLQueryRequest,
    db: Session = Depends(get_db)
):
    """자연어 질의를 SQL로 변환하여 검색합니다."""
    try:
        service = SearchService(db)
        results = await service.natural_language_search(request.query, request.limit)
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")


@router.post("/text", summary="전문 텍스트 검색")
async def text_search(
    request: TextSearchRequest,
    db: Session = Depends(get_db)
):
    """의결서 전문에서 텍스트를 검색합니다."""
    try:
        service = SearchService(db)
        results = service.text_search(request.text, request.limit)
        
        return {
            "query": request.text,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")


@router.get("/suggestions", summary="검색 제안")
async def get_search_suggestions(db: Session = Depends(get_db)):
    """검색 제안 목록을 반환합니다."""
    service = SearchService(db)
    suggestions = service.get_search_suggestions()
    
    return suggestions