from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.fsc_models import Decision, Action
from app.services.decision_service import DecisionService

router = APIRouter()


@router.get("/", summary="의결서 목록 조회")
async def get_decisions(
    skip: int = 0,
    limit: int = 100,
    category_1: Optional[str] = None,
    category_2: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """의결서 목록을 조회합니다."""
    service = DecisionService(db)
    
    filters = {}
    if category_1:
        filters["category_1"] = category_1
    if category_2:
        filters["category_2"] = category_2
    
    decisions = service.get_decisions(skip=skip, limit=limit, filters=filters)
    return decisions


@router.get("/{decision_id}", summary="의결서 상세 조회")
async def get_decision(decision_id: int, db: Session = Depends(get_db)):
    """특정 의결서의 상세 정보를 조회합니다."""
    service = DecisionService(db)
    decision = service.get_decision_by_id(decision_id)
    
    if not decision:
        raise HTTPException(status_code=404, detail="의결서를 찾을 수 없습니다.")
    
    return decision


@router.get("/{decision_id}/actions", summary="의결서 관련 조치 목록")
async def get_decision_actions(decision_id: int, db: Session = Depends(get_db)):
    """특정 의결서와 관련된 조치 목록을 조회합니다."""
    service = DecisionService(db)
    actions = service.get_actions_by_decision_id(decision_id)
    
    return actions


@router.get("/stats/categories", summary="카테고리별 통계")
async def get_category_stats(db: Session = Depends(get_db)):
    """카테고리별 의결서 통계를 조회합니다."""
    service = DecisionService(db)
    stats = service.get_category_stats()
    
    return stats