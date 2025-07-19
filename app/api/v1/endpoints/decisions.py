from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.core.database import get_db
from app.models.fsc_models import Decision, Action, Law
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


@router.get("/stats/categories", summary="카테고리별 통계")
async def get_category_stats(db: Session = Depends(get_db)):
    """카테고리별 의결서 통계를 조회합니다."""
    service = DecisionService(db)
    stats = service.get_category_stats()
    
    return stats


@router.get("/stats/dashboard", summary="대시보드 종합 통계")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """대시보드용 종합 통계를 조회합니다."""
    service = DecisionService(db)
    
    # 기본 통계
    total_decisions = db.query(Decision).count()
    total_actions = db.query(Action).count()
    total_laws = db.query(Law).count()
    
    # 최근 의결서 (상위 5개)
    recent_decisions = (
        db.query(Decision)
        .order_by(
            Decision.decision_year.desc(),
            Decision.decision_id.desc()
        )
        .limit(5)
        .all()
    )
    
    # 총 과징금/과태료 금액
    total_fine_amount = db.query(func.sum(Action.fine_amount)).scalar() or 0
    
    # 월별 의결서 수 (최근 12개월)
    monthly_stats = (
        db.query(
            Decision.decision_year,
            Decision.decision_month,
            func.count(Decision.decision_id).label('count')
        )
        .group_by(Decision.decision_year, Decision.decision_month)
        .order_by(Decision.decision_year.desc(), Decision.decision_month.desc())
        .limit(12)
        .all()
    )
    
    # 카테고리별 통계
    category_stats = service.get_category_stats()
    
    return {
        "summary": {
            "total_decisions": total_decisions,
            "total_actions": total_actions,
            "total_laws": total_laws,
            "total_fine_amount": total_fine_amount
        },
        "recent_decisions": [
            {
                "decision_year": d.decision_year,
                "decision_id": d.decision_id,
                "title": d.title,
                "category_1": d.category_1,
                "category_2": d.category_2,
                "decision_date": d.decision_date.isoformat() if d.decision_date else None
            }
            for d in recent_decisions
        ],
        "monthly_trends": [
            {
                "year": stat[0],
                "month": stat[1],
                "count": stat[2]
            }
            for stat in monthly_stats
        ],
        "categories": category_stats
    }


@router.get("/{decision_year}/{decision_id}", summary="의결서 상세 조회")
async def get_decision(decision_year: int, decision_id: int, db: Session = Depends(get_db)):
    """특정 의결서의 상세 정보를 조회합니다."""
    service = DecisionService(db)
    decision = service.get_decision_by_composite_key(decision_year, decision_id)
    
    if not decision:
        raise HTTPException(status_code=404, detail="의결서를 찾을 수 없습니다.")
    
    return decision


@router.get("/{decision_year}/{decision_id}/actions", summary="의결서 관련 조치 목록")
async def get_decision_actions(decision_year: int, decision_id: int, db: Session = Depends(get_db)):
    """특정 의결서와 관련된 조치 목록을 조회합니다."""
    service = DecisionService(db)
    actions = service.get_actions_by_decision_composite_key(decision_year, decision_id)
    
    return actions


@router.get("/{decision_year}/{decision_id}/laws", summary="의결서 관련 법률 목록")
async def get_decision_laws(decision_year: int, decision_id: int, db: Session = Depends(get_db)):
    """특정 의결서와 관련된 법률 목록을 조회합니다."""
    service = DecisionService(db)
    laws = service.get_laws_by_decision_composite_key(decision_year, decision_id)
    
    return laws