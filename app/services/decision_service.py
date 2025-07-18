from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Dict, Any
from app.models.fsc_models import Decision, Action, Law, ActionLawMap


class DecisionService:
    """의결서 관련 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_decisions(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Decision]:
        """의결서 목록을 조회합니다."""
        query = self.db.query(Decision)
        
        if filters:
            if "category_1" in filters:
                query = query.filter(Decision.category_1 == filters["category_1"])
            if "category_2" in filters:
                query = query.filter(Decision.category_2 == filters["category_2"])
            if "start_date" in filters:
                start_date = filters["start_date"]
                query = query.filter(
                    (Decision.decision_year > start_date.year) |
                    ((Decision.decision_year == start_date.year) & (Decision.decision_month > start_date.month)) |
                    ((Decision.decision_year == start_date.year) & (Decision.decision_month == start_date.month) & (Decision.decision_day >= start_date.day))
                )
            if "end_date" in filters:
                end_date = filters["end_date"]
                query = query.filter(
                    (Decision.decision_year < end_date.year) |
                    ((Decision.decision_year == end_date.year) & (Decision.decision_month < end_date.month)) |
                    ((Decision.decision_year == end_date.year) & (Decision.decision_month == end_date.month) & (Decision.decision_day <= end_date.day))
                )
        
        return query.order_by(
            Decision.decision_year.desc(), 
            Decision.decision_month.desc(), 
            Decision.decision_day.desc()
        ).offset(skip).limit(limit).all()
    
    def get_decision_by_id(self, decision_id: int) -> Optional[Decision]:
        """ID로 의결서를 조회합니다."""
        return self.db.query(Decision).filter(Decision.decision_id == decision_id).first()
    
    def get_actions_by_decision_id(self, decision_id: int) -> List[Action]:
        """특정 의결서와 관련된 조치 목록을 조회합니다."""
        return self.db.query(Action).filter(Action.decision_id == decision_id).all()
    
    def get_category_stats(self) -> Dict[str, Any]:
        """카테고리별 통계를 조회합니다."""
        # 대분류별 통계
        category_1_stats = (
            self.db.query(
                Decision.category_1,
                func.count(Decision.decision_id).label('count')
            )
            .group_by(Decision.category_1)
            .all()
        )
        
        # 중분류별 통계
        category_2_stats = (
            self.db.query(
                Decision.category_1,
                Decision.category_2,
                func.count(Decision.decision_id).label('count')
            )
            .group_by(Decision.category_1, Decision.category_2)
            .all()
        )
        
        # 연도별 통계
        yearly_stats = (
            self.db.query(
                Decision.decision_year.label('year'),
                func.count(Decision.decision_id).label('count')
            )
            .group_by(Decision.decision_year)
            .order_by(Decision.decision_year)
            .all()
        )
        
        return {
            "category_1": [{"category": item[0], "count": item[1]} for item in category_1_stats],
            "category_2": [{"category_1": item[0], "category_2": item[1], "count": item[2]} for item in category_2_stats],
            "yearly": [{"year": item[0], "count": item[1]} for item in yearly_stats]
        }
    
    def create_decision(self, decision_data: Dict[str, Any]) -> Decision:
        """새로운 의결서를 생성합니다."""
        decision = Decision(**decision_data)
        self.db.add(decision)
        self.db.commit()
        self.db.refresh(decision)
        return decision
    
    def update_decision(self, decision_id: int, update_data: Dict[str, Any]) -> Optional[Decision]:
        """의결서를 업데이트합니다."""
        decision = self.get_decision_by_id(decision_id)
        if not decision:
            return None
        
        for key, value in update_data.items():
            setattr(decision, key, value)
        
        self.db.commit()
        self.db.refresh(decision)
        return decision
    
    def delete_decision(self, decision_id: int) -> bool:
        """의결서를 삭제합니다."""
        decision = self.get_decision_by_id(decision_id)
        if not decision:
            return False
        
        self.db.delete(decision)
        self.db.commit()
        return True