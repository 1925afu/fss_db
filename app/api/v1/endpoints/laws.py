from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.fsc_models import Law, ActionLawMap, Action, Decision
from app.services.decision_service import DecisionService

router = APIRouter()


@router.get("/", summary="법률 목록 조회")
async def get_laws(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """법률 목록을 조회합니다."""
    query = db.query(Law)
    
    if category:
        query = query.filter(Law.law_category == category)
    
    laws = query.order_by(Law.law_name).offset(skip).limit(limit).all()
    return laws


@router.get("/{law_id}", summary="법률 상세 조회")
async def get_law(law_id: int, db: Session = Depends(get_db)):
    """특정 법률의 상세 정보를 조회합니다."""
    law = db.query(Law).filter(Law.law_id == law_id).first()
    
    if not law:
        raise HTTPException(status_code=404, detail="법률을 찾을 수 없습니다.")
    
    return law


@router.get("/{law_id}/cases", summary="법률 관련 사례 조회")
async def get_law_cases(
    law_id: int, 
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """특정 법률과 관련된 의결서 사례를 조회합니다."""
    law = db.query(Law).filter(Law.law_id == law_id).first()
    
    if not law:
        raise HTTPException(status_code=404, detail="법률을 찾을 수 없습니다.")
    
    # 해당 법률과 관련된 의결서들 조회
    cases = (
        db.query(Decision, ActionLawMap.article_details, Action.action_type, Action.fine_amount)
        .join(Action)
        .join(ActionLawMap)
        .filter(ActionLawMap.law_id == law_id)
        .order_by(Decision.decision_year.desc(), Decision.decision_id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    results = []
    for decision, article_details, action_type, fine_amount in cases:
        results.append({
            "decision_year": decision.decision_year,
            "decision_id": decision.decision_id,
            "title": decision.title,
            "category_1": decision.category_1,
            "category_2": decision.category_2,
            "decision_date": decision.decision_date.isoformat() if decision.decision_date else None,
            "article_details": article_details,
            "action_type": action_type,
            "fine_amount": fine_amount
        })
    
    return {
        "law": {
            "law_id": law.law_id,
            "law_name": law.law_name,
            "law_short_name": law.law_short_name,
            "law_category": law.law_category
        },
        "cases": results,
        "total_cases": len(results)
    }


@router.get("/stats/usage", summary="법률 사용 통계")
async def get_law_usage_stats(db: Session = Depends(get_db)):
    """법률별 사용 통계를 조회합니다."""
    stats = (
        db.query(
            Law.law_name,
            Law.law_short_name,
            Law.law_category,
            db.func.count(ActionLawMap.law_id).label('usage_count')
        )
        .join(ActionLawMap)
        .group_by(Law.law_id, Law.law_name, Law.law_short_name, Law.law_category)
        .order_by(db.func.count(ActionLawMap.law_id).desc())
        .limit(20)
        .all()
    )
    
    return [
        {
            "law_name": stat[0],
            "law_short_name": stat[1],
            "law_category": stat[2],
            "usage_count": stat[3]
        }
        for stat in stats
    ]


@router.get("/categories/", summary="법률 카테고리 목록")
async def get_law_categories(db: Session = Depends(get_db)):
    """법률 카테고리 목록을 조회합니다."""
    categories = (
        db.query(Law.law_category, db.func.count(Law.law_id).label('count'))
        .group_by(Law.law_category)
        .order_by(db.func.count(Law.law_id).desc())
        .all()
    )
    
    return [
        {"category": category, "count": count}
        for category, count in categories
    ]