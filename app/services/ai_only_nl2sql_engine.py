"""
AI 전용 NL2SQL 엔진
Rule-based 로직을 완전히 제거하고 Gemini-2.5-Flash-Lite만 사용
"""

import re
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.services.gemini_service import GeminiService
from app.models.fsc_models import Decision, Action, Law, ActionLawMap

logger = logging.getLogger(__name__)


class QueryTypeClassifier:
    """사용자 질의를 6가지 유형으로 분류하는 클래스"""
    
    @staticmethod
    def classify_query(query: str) -> str:
        """질의 유형을 자동 분류"""
        query_lower = query.lower()
        
        # 1. 특정 대상 조회 (회사명, 개인명, 업권)
        target_patterns = [
            r'(주식회사|㈜|회사|법인|은행|증권|보험|자산운용)',
            r'(대표이사|임직원|회계사|감사인)',
            r'(\w+은행|\w+증권|\w+보험|\w+자산운용|\w+회계법인)'
        ]
        if any(re.search(pattern, query) for pattern in target_patterns):
            return "specific_target"
        
        # 2. 위반 행위 유형별
        violation_patterns = [
            r'(위반|독립성|회계처리|준법감시|불공정거래|내부통제|공시|정보유출)',
            r'(법률|조항|기준|의무|규정|위반)'
        ]
        if any(re.search(pattern, query) for pattern in violation_patterns):
            return "violation_type"
        
        # 3. 조치 수준별
        action_patterns = [
            r'(과징금|과태료|직무정지|업무정지|기관경고|영업정지|해임)',
            r'(\d+억|\d+천만|\d+백만).*원',
            r'(이상|이하|초과|미만)'
        ]
        if any(re.search(pattern, query) for pattern in action_patterns):
            return "action_level"
        
        # 4. 시점 기반
        time_patterns = [
            r'(\d{4}년|\d+분기|올해|작년|재작년)',
            r'(최근|지난)\s*\d*\s*(년|개월|일)',
            r'(\d+월|\d+일)'
        ]
        if any(re.search(pattern, query) for pattern in time_patterns):
            return "time_based"
        
        # 5. 통계/요약
        stats_patterns = [
            r'(통계|현황|순위|비교|분포|트렌드|요약)',
            r'(top\s*\d+|상위\s*\d+|총\s*\d+)',
            r'(평균|합계|최대|최소|그래프|차트)'
        ]
        if any(re.search(pattern, query) for pattern in stats_patterns):
            return "statistics"
        
        # 6. 복합 조건 (기본값)
        return "complex_condition"


class AIOnlyNL2SQLEngine:
    """완전 AI 기반 NL2SQL 엔진"""
    
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService()
        self.classifier = QueryTypeClassifier()
    
    async def process_natural_query(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """자연어 쿼리를 완전 AI로 처리"""
        try:
            logger.info(f"AI 전용 NL2SQL 처리 시작: {query}")
            
            # 1단계: 질의 유형 자동 분류
            query_type = self.classifier.classify_query(query)
            logger.info(f"질의 유형 분류: {query_type}")
            
            # 2단계: AI로 SQL 생성
            sql_result = await self.gemini_service.convert_nl_to_sql_advanced(
                query, query_type
            )
            
            if not sql_result['success']:
                return {
                    'success': False,
                    'error': sql_result.get('error', 'SQL 생성 실패'),
                    'query_type': query_type
                }
            
            # 3단계: SQL 안전성 검증
            sql_query = sql_result['sql_query']
            if not self._validate_sql_safety(sql_query):
                return {
                    'success': False,
                    'error': 'AI 생성 SQL이 안전성 검증을 통과하지 못했습니다',
                    'sql_query': sql_query
                }
            
            # 4단계: SQL 실행
            execution_result = self._execute_sql_with_validation(sql_query, limit)
            
            if execution_result['success']:
                return {
                    'success': True,
                    'query_type': query_type,
                    'sql_query': sql_query,
                    'results': execution_result['data'],
                    'metadata': {
                        'model_used': 'gemini-2.5-flash-lite-preview-06-17',
                        'query_classification': query_type,
                        'total_rows': len(execution_result['data']),
                        'explanation': sql_result.get('explanation', '')
                    }
                }
            else:
                # 5단계: 실행 실패 시 AI로 재시도
                return await self._retry_with_error_feedback(
                    query, query_type, sql_query, execution_result['error']
                )
                
        except Exception as e:
            logger.error(f"AI 전용 NL2SQL 처리 중 오류: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_available': True
            }
    
    def _validate_sql_safety(self, sql_query: str) -> bool:
        """SQL 안전성 검증"""
        sql_lower = sql_query.lower()
        
        # 위험한 키워드 체크
        dangerous_keywords = [
            'drop', 'delete', 'insert', 'update', 'alter', 'create', 
            'exec', 'execute', 'truncate', '--', ';--'
        ]
        if any(keyword in sql_lower for keyword in dangerous_keywords):
            logger.warning(f"위험한 키워드 감지: {sql_query}")
            return False
        
        # LIMIT 절 필수
        if 'limit' not in sql_lower:
            logger.warning(f"LIMIT 절이 없음: {sql_query}")
            return False
        
        # 허용된 테이블만 사용
        allowed_tables = ['decisions', 'actions', 'laws', 'action_law_map']
        if not any(table in sql_lower for table in allowed_tables):
            logger.warning(f"허용되지 않은 테이블: {sql_query}")
            return False
        
        return True
    
    def _execute_sql_with_validation(self, sql_query: str, limit: int) -> Dict[str, Any]:
        """SQL 실행 및 결과 검증"""
        try:
            # LIMIT 적용 (추가 안전장치)
            if 'limit' in sql_query.lower():
                # 기존 LIMIT 값 확인 및 조정
                limit_match = re.search(r'limit\s+(\d+)', sql_query.lower())
                if limit_match:
                    existing_limit = int(limit_match.group(1))
                    if existing_limit > limit:
                        sql_query = re.sub(
                            r'limit\s+\d+', f'LIMIT {limit}', 
                            sql_query, flags=re.IGNORECASE
                        )
            else:
                sql_query += f" LIMIT {limit}"
            
            # SQL 실행
            result = self.db.execute(text(sql_query))
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            
            logger.info(f"SQL 실행 성공: {len(data)}건 조회")
            
            return {
                'success': True,
                'data': data,
                'row_count': len(data)
            }
            
        except Exception as e:
            logger.error(f"SQL 실행 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'data': []
            }
    
    async def _retry_with_error_feedback(self, original_query: str, query_type: str, 
                                       failed_sql: str, error_message: str) -> Dict[str, Any]:
        """SQL 실행 실패 시 AI에게 오류 피드백하여 재시도"""
        try:
            retry_prompt = f"""
이전 SQL 쿼리가 실행에 실패했습니다. 오류를 수정해서 다시 생성해주세요.

원본 질문: {original_query}
실패한 SQL: {failed_sql}
오류 메시지: {error_message}

SQLite 문법에 맞게 수정하고, 오류를 해결한 새로운 SQL을 생성해주세요.
특히 다음 사항을 확인하세요:
1. SQLite 호환 함수 사용 (strftime 등)
2. 올바른 컬럼명과 테이블명
3. 적절한 JOIN 조건
4. LIMIT 절 포함
"""
            
            retry_result = await self.gemini_service.convert_nl_to_sql_advanced(
                retry_prompt, query_type
            )
            
            if retry_result['success']:
                fixed_sql = retry_result['sql_query']
                
                if self._validate_sql_safety(fixed_sql):
                    execution_result = self._execute_sql_with_validation(fixed_sql, 50)
                    
                    if execution_result['success']:
                        logger.info("AI 재시도로 SQL 수정 및 실행 성공")
                        return {
                            'success': True,
                            'query_type': query_type,
                            'sql_query': fixed_sql,
                            'results': execution_result['data'],
                            'metadata': {
                                'model_used': 'gemini-2.5-flash-lite-preview-06-17',
                                'retry_attempt': True,
                                'original_error': error_message,
                                'total_rows': len(execution_result['data'])
                            }
                        }
            
            # 재시도도 실패한 경우
            return {
                'success': False,
                'error': f'AI 재시도도 실패: {retry_result.get("error", "Unknown")}',
                'original_error': error_message,
                'failed_sql': failed_sql
            }
            
        except Exception as e:
            logger.error(f"AI 재시도 중 오류: {e}")
            return {
                'success': False,
                'error': f'재시도 중 오류: {str(e)}',
                'original_error': error_message
            }
    
    async def get_query_suggestions(self) -> Dict[str, List[str]]:
        """AI 기반 스마트 쿼리 제안"""
        try:
            # 기본 데이터 통계 수집
            total_decisions = self.db.query(Decision).count()
            total_actions = self.db.query(Action).count()
            
            # 최신 연도 확인
            latest_year = self.db.query(Decision.decision_year).order_by(
                Decision.decision_year.desc()
            ).first()
            current_year = latest_year[0] if latest_year else 2025
            
            # 주요 업권 확인
            top_industries = self.db.query(Action.industry_sector).distinct().limit(3).all()
            industries = [ind[0] for ind in top_industries if ind[0]]
            
            # 타입별 제안 생성
            suggestions = {
                "specific_target": [
                    f"신한은행이 {current_year}년에 받은 제재 내역",
                    "엔에이치아문디자산운용 제재 현황",
                    "4대 회계법인 징계 사례"
                ],
                "violation_type": [
                    "독립성 위반으로 징계받은 공인회계사 사례",
                    "회계처리 기준 위반 제재 현황",
                    "내부통제 의무 위반 기관경고 사례"
                ],
                "action_level": [
                    "10억원 이상 과징금 부과 사건",
                    "직무정지 처분을 받은 회계사",
                    "과태료 1억원 이하 경미한 위반"
                ],
                "time_based": [
                    f"{current_year}년 제재 의결 현황",
                    f"최근 3년간 제재 건수 추이",
                    f"작년 4분기 금융위 의결서"
                ],
                "statistics": [
                    "업권별 과징금 총액 순위",
                    "법률 위반 유형별 분포",
                    "연도별 제재 건수 비교"
                ],
                "complex_condition": [
                    f"작년에 회계처리 위반으로 과징금을 받은 {industries[0] if industries else '금융투자'} 업권",
                    "자본시장법 위반으로 1억원 이상 과징금을 받은 자산운용사",
                    "독립성 위반으로 직무정지를 받은 회계사"
                ]
            }
            
            return suggestions
            
        except Exception as e:
            logger.error(f"제안 생성 실패: {e}")
            return {
                "general": [
                    "최근 제재 현황",
                    "과징금 부과 사례",
                    "업권별 제재 통계"
                ]
            }