from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import date
from app.core.database import get_db
from app.models.fsc_models import Action, Decision, Law, ActionLawMap

router = APIRouter()


@router.get("/", summary="조치 목록 조회")
async def get_actions(
    skip: int = 0,
    limit: int = 100,
    action_type: Optional[str] = None,
    industry_sector: Optional[str] = None,
    min_fine_amount: Optional[int] = None,
    max_fine_amount: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """조치 목록을 조회합니다."""
    query = db.query(Action).join(Decision)
    
    if action_type:
        query = query.filter(Action.action_type.like(f"%{action_type}%"))
    
    if industry_sector:
        query = query.filter(Action.industry_sector == industry_sector)
    
    if min_fine_amount is not None:
        query = query.filter(Action.fine_amount >= min_fine_amount)
    
    if max_fine_amount is not None:
        query = query.filter(Action.fine_amount <= max_fine_amount)
    
    actions = (
        query.order_by(
            Decision.decision_year.desc(),
            Decision.decision_id.desc()
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return actions


@router.get("/{action_id}", summary="조치 상세 조회")
async def get_action(action_id: int, db: Session = Depends(get_db)):
    """특정 조치의 상세 정보를 조회합니다."""
    action = db.query(Action).filter(Action.action_id == action_id).first()
    
    if not action:
        raise HTTPException(status_code=404, detail="조치를 찾을 수 없습니다.")
    
    # 관련 법률 정보도 함께 조회
    laws = (
        db.query(Law, ActionLawMap.article_details)
        .join(ActionLawMap)
        .filter(ActionLawMap.action_id == action_id)
        .all()
    )
    
    related_laws = [
        {
            "law_id": law.law_id,
            "law_name": law.law_name,
            "law_short_name": law.law_short_name,
            "article_details": article_details
        }
        for law, article_details in laws
    ]
    
    # 의결서 정보도 함께 조회
    decision = db.query(Decision).filter(
        Decision.decision_year == action.decision_year,
        Decision.decision_id == action.decision_id
    ).first()
    
    return {
        "action": action,
        "related_laws": related_laws,
        "decision": {
            "decision_year": decision.decision_year if decision else None,
            "decision_id": decision.decision_id if decision else None,
            "title": decision.title if decision else None,
            "category_1": decision.category_1 if decision else None,
            "category_2": decision.category_2 if decision else None
        }
    }


@router.get("/stats/summary", summary="조치 통계 요약")
async def get_action_stats_summary(db: Session = Depends(get_db)):
    """조치 관련 통계 요약을 조회합니다."""
    
    # 조치 유형별 통계
    action_type_stats = (
        db.query(
            Action.action_type,
            func.count(Action.action_id).label('count'),
            func.sum(Action.fine_amount).label('total_fine'),
            func.avg(Action.fine_amount).label('avg_fine')
        )
        .filter(Action.action_type.isnot(None))
        .group_by(Action.action_type)
        .order_by(func.count(Action.action_id).desc())
        .all()
    )
    
    # 업권별 통계
    industry_stats = (
        db.query(
            Action.industry_sector,
            func.count(Action.action_id).label('count'),
            func.sum(Action.fine_amount).label('total_fine')
        )
        .filter(Action.industry_sector.isnot(None))
        .group_by(Action.industry_sector)
        .order_by(func.count(Action.action_id).desc())
        .all()
    )
    
    # 연도별 통계
    yearly_stats = (
        db.query(
            Action.decision_year,
            func.count(Action.action_id).label('count'),
            func.sum(Action.fine_amount).label('total_fine')
        )
        .group_by(Action.decision_year)
        .order_by(Action.decision_year.desc())
        .all()
    )
    
    # 전체 통계
    total_actions = db.query(func.count(Action.action_id)).scalar()
    total_fine_amount = db.query(func.sum(Action.fine_amount)).scalar() or 0
    avg_fine_amount = db.query(func.avg(Action.fine_amount)).scalar() or 0
    
    return {
        "summary": {
            "total_actions": total_actions,
            "total_fine_amount": total_fine_amount,
            "average_fine_amount": float(avg_fine_amount)
        },
        "by_action_type": [
            {
                "action_type": row[0],
                "count": row[1],
                "total_fine": row[2] or 0,
                "average_fine": float(row[3]) if row[3] else 0
            }
            for row in action_type_stats
        ],
        "by_industry": [
            {
                "industry_sector": row[0],
                "count": row[1],
                "total_fine": row[2] or 0
            }
            for row in industry_stats
        ],
        "by_year": [
            {
                "year": row[0],
                "count": row[1],
                "total_fine": row[2] or 0
            }
            for row in yearly_stats
        ]
    }


@router.get("/stats/fines", summary="과징금 통계")
async def get_fine_stats(
    min_amount: Optional[int] = Query(None, description="최소 과징금 금액"),
    max_amount: Optional[int] = Query(None, description="최대 과징금 금액"),
    db: Session = Depends(get_db)
):
    """과징금 관련 상세 통계를 조회합니다."""
    query = db.query(Action).filter(Action.fine_amount.isnot(None), Action.fine_amount > 0)
    
    if min_amount is not None:
        query = query.filter(Action.fine_amount >= min_amount)
    
    if max_amount is not None:
        query = query.filter(Action.fine_amount <= max_amount)
    
    # 과징금 범위별 분포
    fine_ranges = [
        (0, 1000000, "100만원 미만"),
        (1000000, 10000000, "100만원 이상 1천만원 미만"),
        (10000000, 50000000, "1천만원 이상 5천만원 미만"),
        (50000000, 100000000, "5천만원 이상 1억원 미만"),
        (100000000, 500000000, "1억원 이상 5억원 미만"),
        (500000000, 1000000000, "5억원 이상 10억원 미만"),
        (1000000000, float('inf'), "10억원 이상")
    ]
    
    range_distribution = []
    for min_val, max_val, label in fine_ranges:
        if max_val == float('inf'):
            count = query.filter(Action.fine_amount >= min_val).count()
        else:
            count = query.filter(
                and_(Action.fine_amount >= min_val, Action.fine_amount < max_val)
            ).count()
        
        range_distribution.append({
            "range": label,
            "count": count
        })
    
    # 상위 과징금 사례
    top_fines = (
        db.query(Action, Decision)
        .join(Decision)
        .filter(Action.fine_amount.isnot(None), Action.fine_amount > 0)
        .order_by(Action.fine_amount.desc())
        .limit(10)
        .all()
    )
    
    top_cases = [
        {
            "entity_name": action.entity_name,
            "fine_amount": action.fine_amount,
            "action_type": action.action_type,
            "decision_title": decision.title,
            "decision_year": decision.decision_year,
            "decision_id": decision.decision_id
        }
        for action, decision in top_fines
    ]
    
    return {
        "distribution": range_distribution,
        "top_cases": top_cases
    }


@router.get("/types/", summary="조치 유형 목록")
async def get_action_types(db: Session = Depends(get_db)):
    """조치 유형 목록을 조회합니다."""
    types = (
        db.query(Action.action_type, func.count(Action.action_id).label('count'))
        .filter(Action.action_type.isnot(None))
        .group_by(Action.action_type)
        .order_by(func.count(Action.action_id).desc())
        .all()
    )
    
    return [
        {"action_type": action_type, "count": count}
        for action_type, count in types
    ]


@router.get("/industries/", summary="업권 목록")
async def get_industries(db: Session = Depends(get_db)):
    """업권 목록을 조회합니다."""
    industries = (
        db.query(Action.industry_sector, func.count(Action.action_id).label('count'))
        .filter(Action.industry_sector.isnot(None))
        .group_by(Action.industry_sector)
        .order_by(func.count(Action.action_id).desc())
        .all()
    )
    
    return [
        {"industry_sector": industry, "count": count}
        for industry, count in industries
    ]