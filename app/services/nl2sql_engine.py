"""
고급 자연어-SQL 변환 엔진
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.services.gemini_service import GeminiService
from app.models.fsc_models import Decision, Action, Law, ActionLawMap

logger = logging.getLogger(__name__)


class NL2SQLEngine:
    """자연어를 SQL로 변환하는 고급 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService()
        
        # 키워드 매핑 사전
        self.keyword_mappings = {
            'action_types': {
                '과태료': ['과태료', '벌금', '범칙금'],
                '과징금': ['과징금', '징수', '부과'],
                '직무정지': ['직무정지', '업무정지', '정지'],
                '경고': ['경고', '주의', '권고'],
                '수사기관 고발': ['고발', '수사기관', '검찰']
            },
            'industries': {
                '은행': ['은행', '은행업', '은행법'],
                '보험': ['보험', '보험업', '보험법', '생명보험', '손해보험'],
                '금융투자': ['금융투자', '증권', '자본시장', '투자', '펀드', '자산운용'],
                '회계/감사': ['회계', '감사', '공인회계사', '감사법인', '외부감사']
            },
            'categories': {
                '제재': ['제재', '처벌', '징계', '과태료', '과징금', '정지'],
                '인허가': ['인허가', '인가', '승인', '허가', '등록', '변경'],
                '정책': ['정책', '법령', '규정', '개정', '제정']
            },
            'amounts': {
                '원': 1,
                '천원': 1000,
                '만원': 10000,
                '십만원': 100000,
                '백만원': 1000000,
                '천만원': 10000000,
                '억원': 100000000,
                '십억원': 1000000000,
                '백억원': 10000000000
            },
            'periods': {
                '올해': 'EXTRACT(YEAR FROM CURRENT_DATE)',
                '작년': 'EXTRACT(YEAR FROM CURRENT_DATE) - 1',
                '재작년': 'EXTRACT(YEAR FROM CURRENT_DATE) - 2',
                '최근 1년': 'EXTRACT(YEAR FROM CURRENT_DATE)',
                '최근 2년': 'EXTRACT(YEAR FROM CURRENT_DATE) - 1',
                '최근 3년': 'EXTRACT(YEAR FROM CURRENT_DATE) - 2'
            }
        }
    
    async def convert_natural_language_to_sql(self, query: str) -> Dict[str, Any]:
        """자연어 쿼리를 SQL로 변환하고 실행"""
        try:
            # 1단계: 쿼리 전처리 및 분석
            analyzed_query = self._analyze_query(query)
            
            # 2단계: Rule-based 변환 시도
            sql_candidates = self._rule_based_conversion(analyzed_query)
            
            # 3단계: AI 변환 (Rule-based 실패 시 또는 복잡한 쿼리)
            if not sql_candidates or analyzed_query['complexity'] == 'high':
                logger.info("AI 기반 SQL 변환 시작")
                ai_sql = await self._ai_based_conversion(query)
                if ai_sql:
                    sql_candidates.append(ai_sql)
            
            # 4단계: SQL 검증 및 실행
            for i, sql_query in enumerate(sql_candidates):
                try:
                    result = self._execute_and_validate_sql(sql_query)
                    if result['success']:
                        return {
                            'success': True,
                            'sql_query': sql_query,
                            'results': result['data'],
                            'metadata': {
                                'method': 'rule_based' if i == 0 else 'ai_based',
                                'analysis': analyzed_query,
                                'total_rows': len(result['data'])
                            }
                        }
                except Exception as e:
                    logger.warning(f"SQL 실행 실패: {sql_query[:100]}... 에러: {e}")
                    continue
            
            # 5단계: 모든 변환 실패 시 폴백
            return await self._fallback_search(query)
            
        except Exception as e:
            logger.error(f"NL2SQL 변환 중 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_results': await self._fallback_search(query)
            }
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """쿼리를 분석하여 의도와 복잡도 파악"""
        analysis = {
            'original_query': query,
            'intent': 'search',  # search, statistics, comparison
            'complexity': 'low',  # low, medium, high
            'entities': {},
            'conditions': {},
            'aggregations': [],
            'time_filters': [],
            'amount_filters': []
        }
        
        query_lower = query.lower()
        
        # 의도 분석
        if any(word in query_lower for word in ['통계', '현황', '분포', '비율', '합계', '평균']):
            analysis['intent'] = 'statistics'
        elif any(word in query_lower for word in ['비교', '대비', '차이', '변화']):
            analysis['intent'] = 'comparison'
        
        # 복잡도 분석
        complexity_indicators = 0
        if '그룹' in query_lower or '분류별' in query_lower or '유형별' in query_lower:
            complexity_indicators += 1
        if any(word in query_lower for word in ['평균', '합계', '최대', '최소']):
            complexity_indicators += 1
        if len(re.findall(r'[0-9]+년|[0-9]+개월|[0-9]+일', query)) > 1:
            complexity_indicators += 1
        
        if complexity_indicators >= 2:
            analysis['complexity'] = 'high'
        elif complexity_indicators == 1:
            analysis['complexity'] = 'medium'
        
        # 엔티티 추출
        analysis['entities'] = self._extract_entities(query)
        
        # 조건 추출
        analysis['conditions'] = self._extract_conditions(query)
        
        return analysis
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """쿼리에서 엔티티 추출 (업권, 조치유형, 법률 등)"""
        entities = {
            'action_types': [],
            'industries': [],
            'categories': [],
            'laws': [],
            'companies': []
        }
        
        query_lower = query.lower()
        
        # 조치 유형 추출
        for action_type, keywords in self.keyword_mappings['action_types'].items():
            if any(keyword in query_lower for keyword in keywords):
                entities['action_types'].append(action_type)
        
        # 업권 추출
        for industry, keywords in self.keyword_mappings['industries'].items():
            if any(keyword in query_lower for keyword in keywords):
                entities['industries'].append(industry)
        
        # 카테고리 추출
        for category, keywords in self.keyword_mappings['categories'].items():
            if any(keyword in query_lower for keyword in keywords):
                entities['categories'].append(category)
        
        # 법률명 추출 (DB에서 검색)
        law_names = self._search_laws_in_query(query)
        entities['laws'] = law_names
        
        return entities
    
    def _extract_conditions(self, query: str) -> Dict[str, Any]:
        """쿼리에서 조건 추출 (금액, 기간 등)"""
        conditions = {
            'amount_range': {},
            'time_range': {},
            'text_search': []
        }
        
        # 금액 조건 추출
        amount_patterns = [
            r'(\d+(?:,\d{3})*)\s*([천만백십억]?원)\s*(이상|이하|초과|미만)',
            r'(이상|이하|초과|미만)\s*(\d+(?:,\d{3})*)\s*([천만백십억]?원)',
            r'(\d+(?:,\d{3})*)\s*([천만백십억]?원)'
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                if len(match) == 3:  # 금액 + 단위 + 조건
                    amount_str, unit, condition = match
                    amount = int(amount_str.replace(',', '')) * self.keyword_mappings['amounts'].get(unit, 1)
                    
                    if condition in ['이상', '초과']:
                        conditions['amount_range']['min'] = amount
                    elif condition in ['이하', '미만']:
                        conditions['amount_range']['max'] = amount
                elif len(match) == 2:  # 금액 + 단위만
                    amount_str, unit = match
                    amount = int(amount_str.replace(',', '')) * self.keyword_mappings['amounts'].get(unit, 1)
                    conditions['amount_range']['min'] = amount  # 기본적으로 이상으로 처리
        
        # 시간 조건 추출
        time_patterns = [
            r'(\d{4})년',
            r'최근\s*(\d+)\s*년',
            r'(올해|작년|재작년)'
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, query)
            for match in matches:
                if match.isdigit():  # 특정 연도
                    if len(match) == 4:  # 2025년
                        conditions['time_range']['year'] = int(match)
                    else:  # 최근 N년
                        conditions['time_range']['recent_years'] = int(match)
                else:  # 올해, 작년 등
                    if match in self.keyword_mappings['periods']:
                        conditions['time_range']['relative'] = match
        
        return conditions
    
    def _search_laws_in_query(self, query: str) -> List[str]:
        """쿼리에서 언급된 법률 검색"""
        try:
            laws = self.db.query(Law).all()
            mentioned_laws = []
            
            for law in laws:
                if law.law_short_name.lower() in query.lower() or law.law_name.lower() in query.lower():
                    mentioned_laws.append(law.law_short_name)
            
            return mentioned_laws
        except Exception as e:
            logger.error(f"법률 검색 중 오류: {e}")
            return []
    
    def _rule_based_conversion(self, analyzed_query: Dict[str, Any]) -> List[str]:
        """규칙 기반 SQL 변환"""
        sql_queries = []
        
        try:
            # 기본 SELECT 절 구성
            if analyzed_query['intent'] == 'statistics':
                sql_query = self._build_statistics_query(analyzed_query)
            else:
                sql_query = self._build_search_query(analyzed_query)
            
            if sql_query:
                sql_queries.append(sql_query)
                
        except Exception as e:
            logger.error(f"Rule-based 변환 실패: {e}")
        
        return sql_queries
    
    def _build_search_query(self, analysis: Dict[str, Any]) -> str:
        """검색용 SQL 쿼리 구성"""
        # 기본 SELECT 절
        select_fields = [
            "d.decision_year",
            "d.decision_id", 
            "d.title",
            "d.category_1",
            "d.category_2",
            "a.entity_name",
            "a.action_type",
            "a.fine_amount",
            "a.industry_sector"
        ]
        
        # FROM 절과 JOIN
        from_clause = "FROM decisions d"
        joins = ["JOIN actions a ON d.decision_year = a.decision_year AND d.decision_id = a.decision_id"]
        
        # 법률 정보가 필요한 경우
        if analysis['entities']['laws']:
            joins.extend([
                "JOIN action_law_map alm ON a.action_id = alm.action_id",
                "JOIN laws l ON alm.law_id = l.law_id"
            ])
            select_fields.extend(["l.law_short_name", "alm.article_details"])
        
        # WHERE 절 구성
        where_conditions = []
        
        # 엔티티 기반 조건
        entities = analysis['entities']
        if entities['action_types']:
            action_conditions = " OR ".join([f"a.action_type LIKE '%{at}%'" for at in entities['action_types']])
            where_conditions.append(f"({action_conditions})")
        
        if entities['industries']:
            industry_conditions = " OR ".join([f"a.industry_sector = '{ind}'" for ind in entities['industries']])
            where_conditions.append(f"({industry_conditions})")
        
        if entities['categories']:
            category_conditions = " OR ".join([f"d.category_1 = '{cat}'" for cat in entities['categories']])
            where_conditions.append(f"({category_conditions})")
        
        if entities['laws']:
            law_conditions = " OR ".join([f"l.law_short_name LIKE '%{law}%'" for law in entities['laws']])
            where_conditions.append(f"({law_conditions})")
        
        # 조건 기반 필터
        conditions = analysis['conditions']
        
        # 금액 조건
        if 'amount_range' in conditions:
            amount_range = conditions['amount_range']
            if 'min' in amount_range:
                where_conditions.append(f"a.fine_amount >= {amount_range['min']}")
            if 'max' in amount_range:
                where_conditions.append(f"a.fine_amount <= {amount_range['max']}")
        
        # 시간 조건
        if 'time_range' in conditions:
            time_range = conditions['time_range']
            if 'year' in time_range:
                where_conditions.append(f"d.decision_year = {time_range['year']}")
            elif 'recent_years' in time_range:
                years_back = time_range['recent_years']
                # SQLite 호환 구문 사용
                where_conditions.append(f"d.decision_year >= (strftime('%Y', 'now') - {years_back})")
            elif 'relative' in time_range:
                relative = time_range['relative']
                if relative in self.keyword_mappings['periods']:
                    # SQLite용 periods 매핑 업데이트 필요
                    periods_sqlite = {
                        '올해': "strftime('%Y', 'now')",
                        '작년': "(strftime('%Y', 'now') - 1)",
                        '재작년': "(strftime('%Y', 'now') - 2)",
                        '최근 1년': "strftime('%Y', 'now')",
                        '최근 2년': "(strftime('%Y', 'now') - 1)",
                        '최근 3년': "(strftime('%Y', 'now') - 2)"
                    }
                    if relative in periods_sqlite:
                        where_conditions.append(f"d.decision_year >= {periods_sqlite[relative]}")
                    else:
                        where_conditions.append(f"d.decision_year >= {self.keyword_mappings['periods'][relative]}")
        
        # 쿼리 조합
        query_parts = [
            f"SELECT {', '.join(select_fields)}",
            from_clause,
            " ".join(joins)
        ]
        
        if where_conditions:
            query_parts.append(f"WHERE {' AND '.join(where_conditions)}")
        
        query_parts.extend([
            "ORDER BY d.decision_year DESC, d.decision_id DESC",
            "LIMIT 50"
        ])
        
        return "\n".join(query_parts)
    
    def _build_statistics_query(self, analysis: Dict[str, Any]) -> str:
        """통계용 SQL 쿼리 구성"""
        # 기본 통계 쿼리 구성
        if '업권별' in analysis['original_query'] or '업권' in analysis['original_query']:
            return """
            SELECT a.industry_sector, 
                   COUNT(*) as case_count,
                   SUM(a.fine_amount) as total_fine,
                   AVG(a.fine_amount) as avg_fine
            FROM decisions d
            JOIN actions a ON d.decision_year = a.decision_year AND d.decision_id = a.decision_id
            WHERE a.industry_sector IS NOT NULL
            GROUP BY a.industry_sector
            ORDER BY case_count DESC
            LIMIT 20
            """
        elif '연도별' in analysis['original_query'] or '년도별' in analysis['original_query']:
            return """
            SELECT d.decision_year,
                   COUNT(*) as case_count,
                   SUM(a.fine_amount) as total_fine
            FROM decisions d
            JOIN actions a ON d.decision_year = a.decision_year AND d.decision_id = a.decision_id
            WHERE d.category_1 = '제재'
            GROUP BY d.decision_year
            ORDER BY d.decision_year DESC
            LIMIT 10
            """
        elif '조치' in analysis['original_query'] and '유형' in analysis['original_query']:
            return """
            SELECT a.action_type,
                   COUNT(*) as case_count,
                   SUM(a.fine_amount) as total_fine
            FROM actions a
            WHERE a.action_type IS NOT NULL
            GROUP BY a.action_type
            ORDER BY case_count DESC
            LIMIT 20
            """
        
        return None
    
    async def _ai_based_conversion(self, query: str) -> Optional[str]:
        """AI 기반 SQL 변환"""
        try:
            sql_query = await self.gemini_service.convert_nl_to_sql(query)
            
            # SQL 안전성 검증
            if self._validate_sql_safety(sql_query):
                return sql_query
            else:
                logger.warning("AI 생성 SQL이 안전성 검증을 통과하지 못했습니다.")
                return None
                
        except Exception as e:
            logger.error(f"AI 기반 SQL 변환 실패: {e}")
            return None
    
    def _validate_sql_safety(self, sql_query: str) -> bool:
        """SQL 쿼리의 안전성 검증"""
        sql_lower = sql_query.lower()
        
        # 위험한 키워드 체크
        dangerous_keywords = ['drop', 'delete', 'insert', 'update', 'alter', 'create', 'exec', '--']
        if any(keyword in sql_lower for keyword in dangerous_keywords):
            return False
        
        # LIMIT 절 확인
        if 'limit' not in sql_lower:
            return False
        
        # 테이블명 검증
        allowed_tables = ['decisions', 'actions', 'laws', 'action_law_map']
        if not any(table in sql_lower for table in allowed_tables):
            return False
        
        return True
    
    def _execute_and_validate_sql(self, sql_query: str) -> Dict[str, Any]:
        """SQL 실행 및 결과 검증"""
        try:
            # SQL 실행
            result = self.db.execute(text(sql_query))
            
            # 결과를 딕셔너리 리스트로 변환
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            
            return {
                'success': True,
                'data': data,
                'row_count': len(data)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': []
            }
    
    async def _fallback_search(self, query: str) -> Dict[str, Any]:
        """폴백 텍스트 검색"""
        try:
            # 간단한 텍스트 검색으로 폴백
            search_term = f"%{query}%"
            
            results = self.db.query(Decision, Action).join(Action).filter(
                Decision.title.like(search_term) |
                Action.entity_name.like(search_term) |
                Action.violation_details.like(search_term)
            ).limit(20).all()
            
            formatted_results = []
            for decision, action in results:
                formatted_results.append({
                    'decision_year': decision.decision_year,
                    'decision_id': decision.decision_id,
                    'title': decision.title,
                    'entity_name': action.entity_name,
                    'action_type': action.action_type,
                    'fine_amount': action.fine_amount
                })
            
            return {
                'success': True,
                'method': 'fallback_text_search',
                'results': formatted_results
            }
            
        except Exception as e:
            logger.error(f"폴백 검색 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }


class QuerySuggestionEngine:
    """쿼리 제안 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_smart_suggestions(self) -> Dict[str, List[str]]:
        """스마트 쿼리 제안 생성"""
        try:
            # 최신 데이터 기반 제안
            recent_year = self.db.query(func.max(Decision.decision_year)).scalar() or 2025
            
            # 주요 업권 조회
            top_industries = self.db.query(Action.industry_sector, func.count(Action.action_id).label('count'))\
                .filter(Action.industry_sector.isnot(None))\
                .group_by(Action.industry_sector)\
                .order_by(func.count(Action.action_id).desc())\
                .limit(3).all()
            
            # 주요 법률 조회
            top_laws = self.db.query(Law.law_short_name, func.count(ActionLawMap.map_id).label('count'))\
                .join(ActionLawMap)\
                .group_by(Law.law_short_name)\
                .order_by(func.count(ActionLawMap.map_id).desc())\
                .limit(3).all()
            
            suggestions = {
                'trending': [
                    f"{recent_year}년 제재 현황",
                    "최근 3년간 과징금 부과 사례",
                    "1억원 이상 과태료 사례"
                ],
                'by_industry': [
                    f"{industry[0]} 업권 제재 현황" for industry in top_industries
                ],
                'by_law': [
                    f"{law[0]} 위반 사례" for law in top_laws
                ],
                'statistics': [
                    "업권별 과징금 통계",
                    "연도별 제재 건수 추이",
                    "조치 유형별 분포"
                ],
                'examples': [
                    "공인회계사 독립성 위반 사례",
                    "가상자산 관련 제재 현황",
                    "최근 1년간 직무정지 처분 사례",
                    "신한은행 관련 조치 내역",
                    "5천만원 이상 과징금 부과 사례"
                ]
            }
            
            return suggestions
            
        except Exception as e:
            logger.error(f"제안 생성 실패: {e}")
            return {
                'trending': ["최근 제재 현황", "과징금 부과 사례"],
                'examples': ["제재 사례 검색", "업권별 현황"]
            }