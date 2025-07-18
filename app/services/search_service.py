from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Dict, Any
from app.models.fsc_models import Decision, Action, Law, ActionLawMap
from app.services.gemini_service import GeminiService


class SearchService:
    """검색 관련 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService()
    
    async def natural_language_search(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """자연어 쿼리를 SQL로 변환하여 검색합니다."""
        try:
            # Gemini를 사용하여 자연어를 SQL로 변환
            sql_query = await self.gemini_service.convert_nl_to_sql(query)
            
            # 생성된 SQL 쿼리 실행
            results = self.db.execute(sql_query).fetchall()
            
            # 결과를 딕셔너리 형태로 변환
            formatted_results = []
            for result in results[:limit]:
                formatted_results.append(dict(result))
            
            return formatted_results
            
        except Exception as e:
            # SQL 변환 실패 시 폴백으로 텍스트 검색 수행
            return self.text_search(query, limit)
    
    def text_search(self, text: str, limit: int = 50) -> List[Dict[str, Any]]:
        """의결서 전문에서 텍스트를 검색합니다."""
        search_term = f"%{text}%"
        
        # 의결서 제목 및 전문에서 검색
        decisions = (
            self.db.query(Decision)
            .filter(
                or_(
                    Decision.title.like(search_term),
                    Decision.full_text.like(search_term),
                    Decision.stated_purpose.like(search_term)
                )
            )
            .limit(limit)
            .all()
        )
        
        # 조치 내용에서 검색
        actions = (
            self.db.query(Action)
            .join(Decision)
            .filter(
                or_(
                    Action.entity_name.like(search_term),
                    Action.violation_details.like(search_term),
                    Action.action_type.like(search_term)
                )
            )
            .limit(limit)
            .all()
        )
        
        # 결과 통합 및 형식화
        results = []
        
        for decision in decisions:
            results.append({
                "type": "decision",
                "id": decision.decision_id,
                "title": decision.title,
                "category_1": decision.category_1,
                "category_2": decision.category_2,
                "decision_date": decision.decision_date.isoformat() if decision.decision_date else None,
                "summary": decision.stated_purpose[:200] + "..." if decision.stated_purpose and len(decision.stated_purpose) > 200 else decision.stated_purpose
            })
        
        for action in actions:
            results.append({
                "type": "action",
                "id": action.action_id,
                "decision_id": action.decision_id,
                "entity_name": action.entity_name,
                "industry_sector": action.industry_sector,
                "action_type": action.action_type,
                "violation_details": action.violation_details[:200] + "..." if action.violation_details and len(action.violation_details) > 200 else action.violation_details,
                "fine_amount": action.fine_amount,
                "effective_date": action.effective_date.isoformat() if action.effective_date else None
            })
        
        return results[:limit]
    
    def get_search_suggestions(self) -> Dict[str, List[str]]:
        """검색 제안 목록을 반환합니다."""
        # 자주 검색되는 키워드들
        common_keywords = [
            "과태료", "직무정지", "업무정지", "인가", "승인", "제재",
            "독립성 위반", "매매제한", "공인회계사", "감사", "은행", "보험",
            "금융투자", "부정", "위반", "징계", "처분"
        ]
        
        # 업권별 분류
        industry_sectors = (
            self.db.query(Action.industry_sector)
            .distinct()
            .filter(Action.industry_sector.isnot(None))
            .all()
        )
        
        # 조치 유형별 분류
        action_types = (
            self.db.query(Action.action_type)
            .distinct()
            .filter(Action.action_type.isnot(None))
            .all()
        )
        
        # 대분류별 분류
        categories = (
            self.db.query(Decision.category_1)
            .distinct()
            .filter(Decision.category_1.isnot(None))
            .all()
        )
        
        return {
            "common_keywords": common_keywords,
            "industry_sectors": [item[0] for item in industry_sectors],
            "action_types": [item[0] for item in action_types],
            "categories": [item[0] for item in categories],
            "sample_queries": [
                "최근 3년간 과태료 부과 사례",
                "공인회계사 독립성 위반 사례",
                "은행 업권 제재 현황",
                "직무정지 처분을 받은 사례",
                "1억원 이상 과징금 부과 사례"
            ]
        }