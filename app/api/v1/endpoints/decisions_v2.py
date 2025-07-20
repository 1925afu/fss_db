from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import os
from app.core.database import get_db
from app.models.fsc_models_v2 import DecisionV2, ActionV2, LawV2
from app.services.decision_service_v2 import DecisionServiceV2
from app.core.config import settings

router = APIRouter()


@router.get("/", summary="V2 의결서 목록 조회")
async def get_decisions(
    skip: int = 0,
    limit: int = 100,
    category_1: Optional[str] = None,
    category_2: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """V2 의결서 목록을 조회합니다."""
    service = DecisionServiceV2(db)
    
    filters = {}
    if category_1:
        filters["category_1"] = category_1
    if category_2:
        filters["category_2"] = category_2
    
    decisions = service.get_decisions(skip=skip, limit=limit, filters=filters)
    return decisions


@router.get("/stats/categories", summary="V2 카테고리별 통계")
async def get_category_stats(db: Session = Depends(get_db)):
    """V2 카테고리별 의결서 통계를 조회합니다."""
    service = DecisionServiceV2(db)
    stats = service.get_category_stats()
    
    return stats


@router.get("/stats/dashboard", summary="V2 대시보드 종합 통계")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """V2 대시보드용 종합 통계를 조회합니다."""
    service = DecisionServiceV2(db)
    
    # 기본 통계
    total_decisions = db.query(DecisionV2).count()
    total_actions = db.query(ActionV2).count()
    total_laws = db.query(LawV2).count()
    
    # 최근 의결서 (상위 5개)
    recent_decisions = (
        db.query(DecisionV2)
        .order_by(
            DecisionV2.decision_year.desc(),
            DecisionV2.decision_id.desc()
        )
        .limit(5)
        .all()
    )
    
    # 총 과징금/과태료 금액
    total_fine_amount = db.query(func.sum(ActionV2.fine_amount)).scalar() or 0
    
    # 월별 의결서 수 (최근 12개월)
    monthly_stats = (
        db.query(
            DecisionV2.decision_year,
            DecisionV2.decision_month,
            func.count(DecisionV2.decision_pk).label('count')
        )
        .group_by(DecisionV2.decision_year, DecisionV2.decision_month)
        .order_by(DecisionV2.decision_year.desc(), DecisionV2.decision_month.desc())
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
                "decision_pk": d.decision_pk,
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


@router.get("/{decision_pk}", summary="V2 의결서 상세 조회 (PK)")
async def get_decision_by_pk(decision_pk: int, db: Session = Depends(get_db)):
    """V2 특정 의결서의 상세 정보를 PK로 조회합니다."""
    service = DecisionServiceV2(db)
    decision = service.get_decision_by_pk(decision_pk)
    
    if not decision:
        raise HTTPException(status_code=404, detail="의결서를 찾을 수 없습니다.")
    
    return decision


@router.get("/{decision_year}/{decision_id}", summary="V2 의결서 상세 조회 (연도/번호)")
async def get_decision(decision_year: int, decision_id: int, db: Session = Depends(get_db)):
    """V2 특정 의결서의 상세 정보를 연도/번호로 조회합니다."""
    service = DecisionServiceV2(db)
    decision = service.get_decision_by_composite_key(decision_year, decision_id)
    
    if not decision:
        raise HTTPException(status_code=404, detail="의결서를 찾을 수 없습니다.")
    
    return decision


@router.get("/{decision_pk}/actions", summary="V2 의결서 관련 조치 목록 (PK)")
async def get_decision_actions_by_pk(decision_pk: int, db: Session = Depends(get_db)):
    """V2 특정 의결서와 관련된 조치 목록을 PK로 조회합니다."""
    service = DecisionServiceV2(db)
    actions = service.get_actions_by_decision_pk(decision_pk)
    
    return actions


@router.get("/{decision_year}/{decision_id}/actions", summary="V2 의결서 관련 조치 목록")
async def get_decision_actions(decision_year: int, decision_id: int, db: Session = Depends(get_db)):
    """V2 특정 의결서와 관련된 조치 목록을 조회합니다."""
    service = DecisionServiceV2(db)
    actions = service.get_actions_by_decision_composite_key(decision_year, decision_id)
    
    return actions


@router.get("/{decision_pk}/laws", summary="V2 의결서 관련 법률 목록 (PK)")
async def get_decision_laws_by_pk(decision_pk: int, db: Session = Depends(get_db)):
    """V2 특정 의결서와 관련된 법률 목록을 PK로 조회합니다."""
    service = DecisionServiceV2(db)
    laws = service.get_laws_by_decision_pk(decision_pk)
    
    return laws


@router.get("/{decision_year}/{decision_id}/laws", summary="V2 의결서 관련 법률 목록")
async def get_decision_laws(decision_year: int, decision_id: int, db: Session = Depends(get_db)):
    """V2 특정 의결서와 관련된 법률 목록을 조회합니다."""
    service = DecisionServiceV2(db)
    laws = service.get_laws_by_decision_composite_key(decision_year, decision_id)
    
    return laws


@router.get("/{decision_year}/{decision_id}/download", summary="V2 의결서 PDF 다운로드")
async def download_decision_pdf(decision_year: int, decision_id: int, db: Session = Depends(get_db)):
    """V2 의결서 PDF 파일을 다운로드합니다."""
    # 의결서 정보 조회
    service = DecisionServiceV2(db)
    decision = service.get_decision_by_composite_key(decision_year, decision_id)
    
    if not decision:
        raise HTTPException(status_code=404, detail="의결서를 찾을 수 없습니다.")
    
    # PDF 파일 경로 생성
    year_dir = os.path.join(settings.PROCESSED_PDF_DIR, str(decision_year))
    
    # source_file이 있는 경우 먼저 시도
    if decision.source_file:
        pdf_path = os.path.join(year_dir, decision.source_file)
        if os.path.exists(pdf_path):
            return FileResponse(
                path=pdf_path,
                filename=decision.source_file,
                media_type="application/pdf"
            )
    
    # source_file이 없거나 파일이 없는 경우, 패턴으로 검색
    # 패턴: 금융위 의결서(제YYYY-XXX호)로 시작하는 파일
    pattern = f"금융위 의결서(제{decision_year}-{decision_id}호)"
    
    if os.path.exists(year_dir):
        for filename in os.listdir(year_dir):
            if filename.startswith(pattern) and filename.endswith('.pdf'):
                pdf_path = os.path.join(year_dir, filename)
                return FileResponse(
                    path=pdf_path,
                    filename=filename,
                    media_type="application/pdf"
                )
    
    raise HTTPException(status_code=404, detail=f"PDF 파일을 찾을 수 없습니다. (패턴: {pattern})")