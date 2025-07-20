from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.core.database import get_db
from app.services.search_service_v2 import SearchServiceV2

router = APIRouter()


class NLQueryRequest(BaseModel):
    """자연어 쿼리 요청 모델"""
    query: str
    limit: Optional[int] = 50


class TextSearchRequest(BaseModel):
    """텍스트 검색 요청 모델"""
    text: str
    limit: Optional[int] = 50


class AdvancedSearchRequest(BaseModel):
    """고급 검색 요청 모델"""
    keyword: Optional[str] = None
    decision_year: Optional[int] = None
    category_1: Optional[str] = None
    category_2: Optional[str] = None
    industry_sector: Optional[str] = None
    action_type: Optional[str] = None
    min_fine_amount: Optional[int] = None
    max_fine_amount: Optional[int] = None
    limit: Optional[int] = 50


@router.post("/nl2sql", summary="V2 자연어 쿼리 검색")
async def natural_language_search(
    request: NLQueryRequest,
    db: Session = Depends(get_db)
):
    """V2 데이터에 대한 자연어 질의를 SQL로 변환하여 검색합니다."""
    try:
        service = SearchServiceV2(db)
        results = await service.natural_language_search(request.query, request.limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")


@router.post("/text", summary="V2 전문 텍스트 검색")
async def text_search(
    request: TextSearchRequest,
    db: Session = Depends(get_db)
):
    """V2 의결서 전문에서 텍스트를 검색합니다."""
    try:
        service = SearchServiceV2(db)
        results = await service.text_search(request.text, request.limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류가 발생했습니다: {str(e)}")


@router.post("/advanced", summary="V2 고급 필터 검색")
async def advanced_search(
    request: AdvancedSearchRequest,
    db: Session = Depends(get_db)
):
    """V2 데이터에 대한 고급 필터를 사용한 조건부 검색을 수행합니다."""
    try:
        service = SearchServiceV2(db)
        criteria = {
            key: value for key, value in request.dict().items() 
            if value is not None and key != 'limit'
        }
        
        results = await service.advanced_search(criteria, request.limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"고급 검색 중 오류가 발생했습니다: {str(e)}")


@router.get("/suggestions", summary="V2 검색 제안")
async def get_search_suggestions(db: Session = Depends(get_db)):
    """V2 검색 제안 목록을 반환합니다."""
    try:
        service = SearchServiceV2(db)
        suggestions = service.get_search_suggestions()
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 제안 조회 중 오류가 발생했습니다: {str(e)}")


@router.get("/stats", summary="V2 검색 관련 통계")
async def get_search_stats(db: Session = Depends(get_db)):
    """V2 검색과 관련된 통계 정보를 반환합니다."""
    try:
        service = SearchServiceV2(db)
        stats = service.get_search_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}")