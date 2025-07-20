from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
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
    start_date: Optional[str] = None  # YYYY-MM 형식
    end_date: Optional[str] = None    # YYYY-MM 형식
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
        
        # results가 이미 딕셔너리 형태로 반환되므로 직접 반환
        return results
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


@router.post("/advanced", summary="고급 필터 검색")
async def advanced_search(
    request: AdvancedSearchRequest,
    db: Session = Depends(get_db)
):
    """고급 필터를 사용한 조건부 검색을 수행합니다."""
    try:
        service = SearchService(db)
        filters = {
            key: value for key, value in request.dict().items() 
            if value is not None and key != 'limit'
        }
        
        results = await service.advanced_search(filters, request.limit)
        
        return {
            "filters": filters,
            "results": results['results'],
            "total_found": results['total_found'],
            "returned_count": results['returned_count'],
            "method": results['method']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"고급 검색 중 오류가 발생했습니다: {str(e)}")


@router.get("/suggestions", summary="검색 제안")
async def get_search_suggestions(db: Session = Depends(get_db)):
    """검색 제안 목록을 반환합니다."""
    service = SearchService(db)
    suggestions = await service.get_search_suggestions()
    
    return suggestions


@router.get("/stats", summary="검색 관련 통계")
async def get_search_stats(db: Session = Depends(get_db)):
    """검색과 관련된 통계 정보를 반환합니다."""
    try:
        service = SearchService(db)
        
        # 기본 통계 수집
        from app.models.fsc_models import Decision, Action, Law
        from sqlalchemy import func
        
        total_decisions = db.query(func.count(Decision.decision_year)).scalar()
        total_actions = db.query(func.count(Action.action_id)).scalar()
        total_laws = db.query(func.count(Law.law_id)).scalar()
        
        # 연도별 분포
        yearly_stats = db.query(
            Decision.decision_year,
            func.count(Decision.decision_id).label('count')
        ).group_by(Decision.decision_year).order_by(Decision.decision_year.desc()).all()
        
        # 업권별 분포
        industry_stats = db.query(
            Action.industry_sector,
            func.count(Action.action_id).label('count')
        ).filter(Action.industry_sector.isnot(None)).group_by(Action.industry_sector).order_by(func.count(Action.action_id).desc()).all()
        
        return {
            "totals": {
                "decisions": total_decisions,
                "actions": total_actions,
                "laws": total_laws
            },
            "yearly_distribution": [{"year": item[0], "count": item[1]} for item in yearly_stats],
            "industry_distribution": [{"sector": item[0], "count": item[1]} for item in industry_stats]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 중 오류가 발생했습니다: {str(e)}")