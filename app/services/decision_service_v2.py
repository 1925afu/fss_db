"""
V2 의결서 관련 비즈니스 로직 처리 서비스
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional, Dict, Any
from app.models.fsc_models_v2 import DecisionV2, ActionV2, LawV2, ActionLawMapV2


class DecisionServiceV2:
    """V2 의결서 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_decisions(self, skip: int = 0, limit: int = 100, filters: Optional[Dict] = None) -> List[DecisionV2]:
        """의결서 목록 조회"""
        query = self.db.query(DecisionV2)
        
        if filters:
            if filters.get("category_1"):
                query = query.filter(DecisionV2.category_1 == filters["category_1"])
            if filters.get("category_2"):
                query = query.filter(DecisionV2.category_2 == filters["category_2"])
        
        return query.order_by(
            DecisionV2.decision_year.desc(), 
            DecisionV2.decision_id.desc()
        ).offset(skip).limit(limit).all()
    
    def get_decision_by_pk(self, decision_pk: int) -> Optional[DecisionV2]:
        """PK로 의결서 조회"""
        return self.db.query(DecisionV2).filter(
            DecisionV2.decision_pk == decision_pk
        ).first()
    
    def get_decision_by_composite_key(self, decision_year: int, decision_id: int) -> Optional[DecisionV2]:
        """복합키(연도, 번호)로 의결서 조회"""
        return self.db.query(DecisionV2).filter(
            and_(
                DecisionV2.decision_year == decision_year,
                DecisionV2.decision_id == decision_id
            )
        ).first()
    
    def get_actions_by_decision_pk(self, decision_pk: int) -> List[ActionV2]:
        """의결서 PK로 관련 조치 목록 조회"""
        return self.db.query(ActionV2).filter(
            ActionV2.decision_pk == decision_pk
        ).all()
    
    def get_actions_by_decision_composite_key(self, decision_year: int, decision_id: int) -> List[ActionV2]:
        """의결서 복합키로 관련 조치 목록 조회"""
        # 먼저 decision_pk를 조회
        decision = self.get_decision_by_composite_key(decision_year, decision_id)
        if not decision:
            return []
        
        return self.get_actions_by_decision_pk(decision.decision_pk)
    
    def get_laws_by_decision_pk(self, decision_pk: int) -> List[LawV2]:
        """의결서 PK로 관련 법률 목록 조회"""
        # 의결서와 관련된 모든 Action들의 Law 조회
        return self.db.query(LawV2).distinct().join(
            ActionLawMapV2,
            ActionLawMapV2.law_id == LawV2.law_id
        ).join(
            ActionV2,
            ActionV2.action_id == ActionLawMapV2.action_id
        ).filter(
            ActionV2.decision_pk == decision_pk
        ).all()
    
    def get_laws_by_decision_composite_key(self, decision_year: int, decision_id: int) -> List[LawV2]:
        """의결서 복합키로 관련 법률 목록 조회"""
        # 먼저 decision_pk를 조회
        decision = self.get_decision_by_composite_key(decision_year, decision_id)
        if not decision:
            return []
        
        return self.get_laws_by_decision_pk(decision.decision_pk)
    
    def get_category_stats(self) -> Dict[str, Any]:
        """카테고리별 통계 조회"""
        # 대분류별 통계
        category_1_stats = self.db.query(
            DecisionV2.category_1,
            func.count(DecisionV2.decision_pk).label('count')
        ).group_by(DecisionV2.category_1).all()
        
        # 중분류별 통계
        category_2_stats = self.db.query(
            DecisionV2.category_2,
            func.count(DecisionV2.decision_pk).label('count')
        ).group_by(DecisionV2.category_2).all()
        
        # 대분류-중분류 조합 통계
        combined_stats = self.db.query(
            DecisionV2.category_1,
            DecisionV2.category_2,
            func.count(DecisionV2.decision_pk).label('count')
        ).group_by(
            DecisionV2.category_1,
            DecisionV2.category_2
        ).all()
        
        return {
            "category_1": [
                {"name": stat[0], "count": stat[1]}
                for stat in category_1_stats
            ],
            "category_2": [
                {"name": stat[0], "count": stat[1]}
                for stat in category_2_stats
            ],
            "combined": [
                {
                    "category_1": stat[0],
                    "category_2": stat[1],
                    "count": stat[2]
                }
                for stat in combined_stats
            ]
        }
    
    def get_action_type_stats(self) -> List[Dict[str, Any]]:
        """조치 유형별 통계 조회"""
        stats = self.db.query(
            ActionV2.action_type,
            func.count(ActionV2.action_pk).label('count')
        ).group_by(ActionV2.action_type).all()
        
        return [
            {"action_type": stat[0], "count": stat[1]}
            for stat in stats
        ]
    
    def get_industry_sector_stats(self) -> List[Dict[str, Any]]:
        """업권별 통계 조회"""
        stats = self.db.query(
            ActionV2.industry_sector,
            func.count(ActionV2.action_pk).label('count')
        ).group_by(ActionV2.industry_sector).all()
        
        return [
            {"industry_sector": stat[0], "count": stat[1]}
            for stat in stats
        ]
    
    def get_yearly_stats(self) -> List[Dict[str, Any]]:
        """연도별 통계 조회"""
        stats = self.db.query(
            DecisionV2.decision_year,
            func.count(DecisionV2.decision_pk).label('count')
        ).group_by(DecisionV2.decision_year).order_by(DecisionV2.decision_year.desc()).all()
        
        return [
            {"year": stat[0], "count": stat[1]}
            for stat in stats
        ]