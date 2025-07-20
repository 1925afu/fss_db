from sqlalchemy.orm import Session
from sqlalchemy import or_, func, text
from typing import List, Dict, Any
import logging
from app.models.fsc_models_v2 import DecisionV2, ActionV2, LawV2, ActionLawMapV2
from app.services.gemini_service import GeminiService
from app.services.ai_only_nl2sql_engine_v2 import AIOnlyNL2SQLEngineV2

logger = logging.getLogger(__name__)


class SearchServiceV2:
    """V2 고급 검색 관련 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService()
        self.ai_nl2sql_engine = AIOnlyNL2SQLEngineV2(db)
    
    def _get_laws_for_action(self, action_id: int) -> List[Dict[str, str]]:
        """특정 조치에 대한 법률 정보 조회"""
        laws = self.db.query(
            LawV2.law_name,
            ActionLawMapV2.article_details
        ).join(
            ActionLawMapV2,
            ActionLawMapV2.law_id == LawV2.law_id
        ).filter(
            ActionLawMapV2.action_id == action_id
        ).all()
        
        return [
            {
                'law_name': law.law_name,
                'article_details': law.article_details
            }
            for law in laws
        ]
    
    async def natural_language_search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """AI 전용 자연어 쿼리 검색 (V2)"""
        try:
            logger.info(f"AI 전용 자연어 검색 시작 (V2): {query}")
            
            # AI 전용 NL2SQL 엔진 사용
            result = await self.ai_nl2sql_engine.process_natural_query(query, limit)
            
            if result['success']:
                return {
                    'query': query,
                    'method': 'ai_only_v2',
                    'query_type': result.get('query_type', 'unknown'),
                    'sql_query': result.get('sql_query', ''),
                    'results': result['results'],
                    'total_found': len(result['results']),
                    'returned_count': len(result['results']),
                    'metadata': result.get('metadata', {})
                }
            else:
                # AI 실패 시 폴백
                logger.warning(f"AI 검색 실패, 폴백 검색 시도: {result.get('error', 'Unknown error')}")
                return await self.fallback_search(query, limit)
                
        except Exception as e:
            logger.error(f"자연어 검색 오류: {e}")
            return {
                'query': query,
                'method': 'error',
                'results': [],
                'total_found': 0,
                'returned_count': 0,
                'error': str(e)
            }
    
    async def text_search(self, text: str, limit: int = 50) -> Dict[str, Any]:
        """텍스트 기반 검색 (V2)"""
        try:
            query = self.db.query(DecisionV2).join(
                ActionV2, DecisionV2.decision_pk == ActionV2.decision_pk
            ).filter(
                or_(
                    DecisionV2.title.contains(text),
                    DecisionV2.stated_purpose.contains(text),
                    ActionV2.entity_name.contains(text),
                    ActionV2.violation_summary.contains(text)
                )
            ).distinct()
            
            decisions = query.limit(limit).all()
            
            results = []
            for decision in decisions:
                result = {
                    'decision_pk': decision.decision_pk,
                    'decision_id': decision.decision_id,
                    'decision_year': decision.decision_year,
                    'title': decision.title,
                    'category_1': decision.category_1,
                    'category_2': decision.category_2,
                    'stated_purpose': decision.stated_purpose
                }
                
                # 관련 조치 정보 추가
                actions = self.db.query(ActionV2).filter(
                    ActionV2.decision_pk == decision.decision_pk
                ).all()
                
                if actions:
                    result['entity_name'] = actions[0].entity_name
                    result['industry_sector'] = actions[0].industry_sector
                    result['action_type'] = actions[0].action_type
                    result['fine_amount'] = sum(a.fine_amount or 0 for a in actions)
                    result['violation_details'] = actions[0].violation_details
                    
                    # 법률 정보 추가
                    laws = []
                    for action in actions:
                        action_laws = self._get_laws_for_action(action.action_id)
                        laws.extend(action_laws)
                    
                    # 중복 제거
                    unique_laws = {}
                    for law in laws:
                        key = f"{law['law_name']}_{law['article_details']}"
                        unique_laws[key] = law
                    
                    result['laws'] = list(unique_laws.values())
                
                results.append(result)
            
            return {
                'query': text,
                'method': 'text_search_v2',
                'results': results,
                'total_found': len(results),
                'returned_count': len(results)
            }
            
        except Exception as e:
            logger.error(f"텍스트 검색 오류: {e}")
            return {
                'query': text,
                'method': 'error',
                'results': [],
                'total_found': 0,
                'returned_count': 0,
                'error': str(e)
            }
    
    async def advanced_search(self, criteria: Dict[str, Any], limit: int = 50) -> Dict[str, Any]:
        """고급 검색 (V2)"""
        try:
            query = self.db.query(DecisionV2).join(
                ActionV2, DecisionV2.decision_pk == ActionV2.decision_pk, isouter=True
            )
            
            # 조건별 필터링
            if criteria.get('keyword'):
                query = query.filter(
                    or_(
                        DecisionV2.title.contains(criteria['keyword']),
                        DecisionV2.stated_purpose.contains(criteria['keyword']),
                        ActionV2.entity_name.contains(criteria['keyword']),
                        ActionV2.violation_summary.contains(criteria['keyword'])
                    )
                )
            
            if criteria.get('decision_year'):
                query = query.filter(DecisionV2.decision_year == criteria['decision_year'])
            
            if criteria.get('category_1'):
                query = query.filter(DecisionV2.category_1 == criteria['category_1'])
            
            if criteria.get('category_2'):
                query = query.filter(DecisionV2.category_2 == criteria['category_2'])
            
            if criteria.get('industry_sector'):
                query = query.filter(ActionV2.industry_sector == criteria['industry_sector'])
            
            if criteria.get('action_type'):
                query = query.filter(ActionV2.action_type == criteria['action_type'])
            
            if criteria.get('min_fine_amount'):
                query = query.filter(ActionV2.fine_amount >= criteria['min_fine_amount'])
            
            if criteria.get('max_fine_amount'):
                query = query.filter(ActionV2.fine_amount <= criteria['max_fine_amount'])
            
            decisions = query.distinct().limit(limit).all()
            
            results = []
            for decision in decisions:
                result = {
                    'decision_pk': decision.decision_pk,
                    'decision_id': decision.decision_id,
                    'decision_year': decision.decision_year,
                    'title': decision.title,
                    'category_1': decision.category_1,
                    'category_2': decision.category_2,
                    'stated_purpose': decision.stated_purpose
                }
                
                # 관련 조치 정보 추가
                actions = self.db.query(ActionV2).filter(
                    ActionV2.decision_pk == decision.decision_pk
                ).all()
                
                if actions:
                    result['entity_name'] = ', '.join([a.entity_name for a in actions])
                    result['industry_sector'] = actions[0].industry_sector
                    result['action_type'] = ', '.join(set([a.action_type for a in actions if a.action_type]))
                    result['fine_amount'] = sum(a.fine_amount or 0 for a in actions)
                    result['violation_details'] = actions[0].violation_details
                    
                    # 법률 정보 추가
                    laws = []
                    for action in actions:
                        action_laws = self._get_laws_for_action(action.action_id)
                        laws.extend(action_laws)
                    
                    # 중복 제거
                    unique_laws = {}
                    for law in laws:
                        key = f"{law['law_name']}_{law['article_details']}"
                        unique_laws[key] = law
                    
                    result['laws'] = list(unique_laws.values())
                
                results.append(result)
            
            return {
                'criteria': criteria,
                'method': 'advanced_search_v2',
                'results': results,
                'total_found': len(results),
                'returned_count': len(results)
            }
            
        except Exception as e:
            logger.error(f"고급 검색 오류: {e}")
            return {
                'criteria': criteria,
                'method': 'error',
                'results': [],
                'total_found': 0,
                'returned_count': 0,
                'error': str(e)
            }
    
    async def fallback_search(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """폴백 검색 (단순 텍스트 매칭) (V2)"""
        try:
            return await self.text_search(query, limit)
        except Exception as e:
            logger.error(f"폴백 검색 오류: {e}")
            return {
                'query': query,
                'method': 'fallback_error',
                'results': [],
                'total_found': 0,
                'returned_count': 0,
                'error': str(e)
            }
    
    def get_search_stats(self) -> Dict[str, Any]:
        """검색 통계 (V2)"""
        try:
            # 기본 통계
            total_decisions = self.db.query(DecisionV2).count()
            total_actions = self.db.query(ActionV2).count()
            total_laws = self.db.query(LawV2).count()
            
            # 연도별 분포
            yearly_dist = self.db.query(
                DecisionV2.decision_year,
                func.count(DecisionV2.decision_pk).label('count')
            ).group_by(DecisionV2.decision_year).all()
            
            # 업권별 분포
            industry_dist = self.db.query(
                ActionV2.industry_sector,
                func.count(ActionV2.action_id).label('count')
            ).filter(ActionV2.industry_sector.isnot(None)).group_by(
                ActionV2.industry_sector
            ).all()
            
            return {
                'totals': {
                    'decisions': total_decisions,
                    'actions': total_actions,
                    'laws': total_laws
                },
                'yearly_distribution': [
                    {'year': year, 'count': count}
                    for year, count in yearly_dist
                ],
                'industry_distribution': [
                    {'sector': sector, 'count': count}
                    for sector, count in industry_dist
                ]
            }
            
        except Exception as e:
            logger.error(f"통계 조회 오류: {e}")
            return {
                'totals': {'decisions': 0, 'actions': 0, 'laws': 0},
                'yearly_distribution': [],
                'industry_distribution': []
            }
    
    def get_search_suggestions(self) -> Dict[str, Any]:
        """검색 제안 (V2)"""
        try:
            # 기본 키워드 제안
            basic_keywords = [
                "과태료", "과징금", "직무정지", "업무정지", 
                "경고", "독립성 위반", "공인회계사", "감사", "제재"
            ]
            
            # 업권별 통계
            industry_sectors = self.db.query(
                ActionV2.industry_sector,
                func.count(ActionV2.action_id).label('count')
            ).filter(ActionV2.industry_sector.isnot(None)).group_by(
                ActionV2.industry_sector
            ).order_by(func.count(ActionV2.action_id).desc()).limit(10).all()
            
            # 조치 유형별 통계
            action_types = self.db.query(
                ActionV2.action_type,
                func.count(ActionV2.action_id).label('count')
            ).filter(ActionV2.action_type.isnot(None)).group_by(
                ActionV2.action_type
            ).order_by(func.count(ActionV2.action_id).desc()).limit(10).all()
            
            # 카테고리별 통계
            categories = self.db.query(
                DecisionV2.category_1,
                func.count(DecisionV2.decision_pk).label('count')
            ).filter(DecisionV2.category_1.isnot(None)).group_by(
                DecisionV2.category_1
            ).all()
            
            return {
                'basic_keywords': basic_keywords,
                'industry_sectors': [
                    f"{sector} ({count}건)" for sector, count in industry_sectors
                ],
                'action_types': [
                    f"{action_type} ({count}건)" for action_type, count in action_types
                ],
                'categories': [
                    f"{category} ({count}건)" for category, count in categories
                ],
                'common_queries': [
                    "최근 3년간 과태료 부과 사례",
                    "공인회계사 독립성 위반 사례",
                    "은행 업권 제재 현황",
                    "직무정지 처분을 받은 사례",
                    "1억원 이상 과징금 부과 사례"
                ],
                'specific_target': [
                    "2025년에 받은 제재 내역",
                    "자산운용사 제재 현황",
                    "회계법인 징계 사례"
                ],
                'violation_type': [
                    "독립성 위반으로 징계받은 공인회계사 사례",
                    "회계처리 기준 위반 제재 현황",
                    "내부통제 의무 위반 기관경고 사례"
                ],
                'action_level': [
                    "10억원 이상 과징금 부과 사건",
                    "직무정지 처분을 받은 회계사",
                    "과태료 1억원 이하 경미한 위반"
                ],
                'time_based': [
                    "2025년 제재 의결 현황",
                    "최근 3년간 제재 건수 추이",
                    "작년 4분기 금융위 의결서"
                ],
                'statistics': [
                    "업권별 과징금 총액 순위",
                    "법률 위반 유형별 분포",
                    "연도별 제재 건수 비교"
                ],
                'complex_condition': [
                    "작년에 회계처리 위반으로 과징금을 받은 금융투자 업권",
                    "자본시장법 위반으로 1억원 이상 과징금을 받은 자산운용사",
                    "독립성 위반으로 직무정지를 받은 회계사"
                ]
            }
            
        except Exception as e:
            logger.error(f"검색 제안 조회 오류: {e}")
            return {
                'basic_keywords': [],
                'industry_sectors': [],
                'action_types': [],
                'categories': [],
                'common_queries': []
            }