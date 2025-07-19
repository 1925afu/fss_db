from sqlalchemy.orm import Session
from sqlalchemy import or_, func, text
from typing import List, Dict, Any
import logging
from app.models.fsc_models import Decision, Action, Law, ActionLawMap
from app.services.gemini_service import GeminiService
from app.services.ai_only_nl2sql_engine import AIOnlyNL2SQLEngine

logger = logging.getLogger(__name__)


class SearchService:
    """고급 검색 관련 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService()
        self.ai_nl2sql_engine = AIOnlyNL2SQLEngine(db)
    
    async def natural_language_search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """AI 전용 자연어 쿼리 검색"""
        try:
            logger.info(f"AI 전용 자연어 검색 시작: {query}")
            
            # AI 전용 NL2SQL 엔진 사용
            result = await self.ai_nl2sql_engine.process_natural_query(query, limit)
            
            if result['success']:
                return {
                    'query': query,
                    'method': 'ai_only',
                    'query_type': result.get('query_type', 'unknown'),
                    'sql_query': result.get('sql_query', ''),
                    'results': result['results'],
                    'total_found': len(result['results']),
                    'returned_count': len(result['results']),
                    'metadata': result.get('metadata', {})
                }
            else:
                # AI 실패 시 폴백
                if result.get('fallback_available'):
                    text_results = self.text_search(query, limit)
                    return {
                        'query': query,
                        'method': 'text_search_fallback',
                        'results': text_results,
                        'total_found': len(text_results),
                        'returned_count': len(text_results),
                        'error': result.get('error'),
                        'ai_error': True
                    }
                else:
                    return {
                        'query': query,
                        'method': 'failed',
                        'results': [],
                        'total_found': 0,
                        'returned_count': 0,
                        'error': result.get('error'),
                        'ai_error': True
                    }
                    
        except Exception as e:
            logger.error(f"AI 자연어 검색 중 오류: {e}")
            # 최종 폴백: 텍스트 검색
            text_results = self.text_search(query, limit)
            return {
                'query': query,
                'method': 'text_search_fallback',
                'results': text_results,
                'total_found': len(text_results),
                'returned_count': len(text_results),
                'error': str(e),
                'fallback_used': True
            }
    
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
    
    async def get_search_suggestions(self) -> Dict[str, List[str]]:
        """AI 기반 검색 제안 목록을 반환합니다."""
        try:
            # AI 엔진의 스마트 제안 사용
            ai_suggestions = await self.ai_nl2sql_engine.get_query_suggestions()
            
            # 기본 제안 추가
            basic_suggestions = self._get_basic_suggestions()
            
            # 통합 결과 반환
            return {
                **ai_suggestions,
                **basic_suggestions
            }
            
        except Exception as e:
            logger.error(f"검색 제안 생성 중 오류: {e}")
            return self._get_basic_suggestions()
    
    def _get_basic_suggestions(self) -> Dict[str, List[str]]:
        """기본 검색 제안"""
        try:
            # 업권별 분류
            industry_sectors = (
                self.db.query(Action.industry_sector, func.count(Action.action_id).label('count'))
                .filter(Action.industry_sector.isnot(None))
                .group_by(Action.industry_sector)
                .order_by(func.count(Action.action_id).desc())
                .all()
            )
            
            # 조치 유형별 분류
            action_types = (
                self.db.query(Action.action_type, func.count(Action.action_id).label('count'))
                .filter(Action.action_type.isnot(None))
                .group_by(Action.action_type)
                .order_by(func.count(Action.action_id).desc())
                .all()
            )
            
            # 대분류별 분류
            categories = (
                self.db.query(Decision.category_1, func.count(Decision.decision_id).label('count'))
                .filter(Decision.category_1.isnot(None))
                .group_by(Decision.category_1)
                .order_by(func.count(Decision.decision_id).desc())
                .all()
            )
            
            return {
                "basic_keywords": [
                    "과태료", "과징금", "직무정지", "업무정지", "경고", 
                    "독립성 위반", "공인회계사", "감사", "제재"
                ],
                "industry_sectors": [f"{item[0]} ({item[1]}건)" for item in industry_sectors],
                "action_types": [f"{item[0]} ({item[1]}건)" for item in action_types],
                "categories": [f"{item[0]} ({item[1]}건)" for item in categories],
                "common_queries": [
                    "최근 3년간 과태료 부과 사례",
                    "공인회계사 독립성 위반 사례", 
                    "은행 업권 제재 현황",
                    "직무정지 처분을 받은 사례",
                    "1억원 이상 과징금 부과 사례",
                    "가상자산 관련 제재 현황",
                    "신한은행 관련 조치 내역"
                ]
            }
            
        except Exception as e:
            logger.error(f"기본 제안 생성 중 오류: {e}")
            return {
                "basic_keywords": ["과태료", "과징금", "제재", "은행", "보험"],
                "common_queries": ["최근 제재 현황", "과징금 부과 사례"]
            }
    
    async def advanced_search(self, filters: Dict[str, Any], limit: int = 50) -> Dict[str, Any]:
        """고급 필터 검색"""
        try:
            # 쿼리 빌더
            query = self.db.query(Decision, Action).join(Action)
            
            # 필터 적용
            if filters.get('decision_year'):
                query = query.filter(Decision.decision_year == filters['decision_year'])
            
            if filters.get('category_1'):
                query = query.filter(Decision.category_1 == filters['category_1'])
            
            if filters.get('category_2'):
                query = query.filter(Decision.category_2 == filters['category_2'])
            
            if filters.get('industry_sector'):
                query = query.filter(Action.industry_sector == filters['industry_sector'])
            
            if filters.get('action_type'):
                query = query.filter(Action.action_type.like(f"%{filters['action_type']}%"))
            
            if filters.get('min_fine_amount'):
                query = query.filter(Action.fine_amount >= filters['min_fine_amount'])
            
            if filters.get('max_fine_amount'):
                query = query.filter(Action.fine_amount <= filters['max_fine_amount'])
            
            if filters.get('start_date'):
                start_year, start_month = filters['start_date'].split('-')
                query = query.filter(
                    (Decision.decision_year > int(start_year)) |
                    ((Decision.decision_year == int(start_year)) & (Decision.decision_month >= int(start_month)))
                )
            
            if filters.get('end_date'):
                end_year, end_month = filters['end_date'].split('-')
                query = query.filter(
                    (Decision.decision_year < int(end_year)) |
                    ((Decision.decision_year == int(end_year)) & (Decision.decision_month <= int(end_month)))
                )
            
            # 검색어 필터
            if filters.get('keyword'):
                keyword = f"%{filters['keyword']}%"
                query = query.filter(
                    Decision.title.like(keyword) |
                    Action.entity_name.like(keyword) |
                    Action.violation_details.like(keyword)
                )
            
            # 결과 조회
            results = query.order_by(
                Decision.decision_year.desc(),
                Decision.decision_id.desc()
            ).limit(limit).all()
            
            # 결과 포맷팅
            formatted_results = []
            for decision, action in results:
                formatted_results.append({
                    'decision_year': decision.decision_year,
                    'decision_id': decision.decision_id,
                    'title': decision.title,
                    'category_1': decision.category_1,
                    'category_2': decision.category_2,
                    'entity_name': action.entity_name,
                    'industry_sector': action.industry_sector,
                    'action_type': action.action_type,
                    'fine_amount': action.fine_amount,
                    'decision_date': f"{decision.decision_year}-{decision.decision_month:02d}-{decision.decision_day:02d}"
                })
            
            return {
                'success': True,
                'method': 'advanced_search',
                'filters': filters,
                'results': formatted_results,
                'total_found': len(formatted_results),
                'returned_count': len(formatted_results)
            }
            
        except Exception as e:
            logger.error(f"고급 검색 중 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }