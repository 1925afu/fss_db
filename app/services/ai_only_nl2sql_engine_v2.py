"""
AI 전용 NL2SQL 엔진 V2
V2 테이블 스키마를 사용하는 자연어 쿼리 처리 엔진
"""
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.services.gemini_service import GeminiService
from app.models.fsc_models_v2 import LawV2, ActionLawMapV2
import json
import re

logger = logging.getLogger(__name__)


class AIOnlyNL2SQLEngineV2:
    """AI 전용 NL2SQL 엔진 V2"""
    
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService()
        
    def get_v2_schema_description(self) -> str:
        """V2 데이터베이스 스키마 설명"""
        return """
        우리 데이터베이스는 금융위원회의 제재 관련 의결서 정보를 저장합니다.
        
        주요 테이블:
        1. decisions_v2 (의결서):
           - decision_pk: 고유 ID (Primary Key)
           - decision_year: 의결 연도
           - decision_id: 의결 번호
           - title: 의결서 제목
           - category_1: 대분류 (제재/인허가/정책)
           - category_2: 중분류 (기관/임직원/전문가/기타)
           - submitter: 제출자 (주로 금융감독원)
           - stated_purpose: 목적
           - full_text: 전문
           - decision_month, decision_day: 의결 월, 일
           
        2. actions_v2 (조치):
           - action_id: 고유 ID (Primary Key)  
           - decision_pk: 의결서 ID (Foreign Key)
           - entity_name: 제재 대상 기관/개인명
           - industry_sector: 업권 (금융투자, 은행, 보험 등)
           - action_type: 조치 유형 (과태료, 과징금, 직무정지, 경고 등)
           - fine_amount: 과태료/과징금 금액 (원 단위)
           - violation_summary: 위반 내용 요약
           - violation_details: 위반 상세 내용
           
        3. laws_v2 (법률):
           - law_pk: 고유 ID (Primary Key)
           - law_name: 법률명
           - law_short_name: 법률 약칭
           - law_type: 법률 유형 (법률, 대통령령, 총리령)
           - law_category: 법률 카테고리
           
        4. action_law_map_v2 (조치-법률 매핑):
           - map_pk: 고유 ID (Primary Key)
           - action_pk: 조치 ID (Foreign Key)
           - law_pk: 법률 ID (Foreign Key)
           - article_details: 관련 조항
           - article_purpose: 조항 목적/내용
           
        관계:
        - 하나의 의결서(decisions_v2)는 여러 조치(actions_v2)를 가질 수 있음
        - 하나의 조치(actions_v2)는 여러 법률(laws_v2)과 연관될 수 있음 (M:N 관계)
        
        주의사항:
        - 금액은 원 단위로 저장됨 (1억원 = 100000000)
        - 날짜는 decision_year, decision_month, decision_day로 분리 저장
        - 일부 필드는 NULL일 수 있음
        """
    
    def create_nl2sql_prompt(self, query: str) -> str:
        """NL2SQL 변환을 위한 프롬프트 생성"""
        return f"""당신은 한국어 자연어 쿼리를 SQL로 변환하는 전문가입니다.
        
{self.get_v2_schema_description()}

사용자 쿼리: "{query}"

위 쿼리를 V2 테이블을 사용하는 SQL로 변환하세요. 다음 규칙을 따르세요:

1. 모든 테이블명 끝에 "_v2"를 붙여야 합니다 (decisions_v2, actions_v2, laws_v2, action_law_map_v2)
2. 의결서는 decision_pk로 식별하고, 조치는 action_id로 식별합니다
3. **중요: 항상 decision_pk, decision_id, decision_year를 SELECT에 포함시켜야 합니다**
4. **중요: actions_v2를 조회할 때는 항상 action_id도 SELECT에 포함시켜야 합니다**
5. 금액 관련 조건은 원 단위로 계산하세요 (1억원 = 100000000)
6. 날짜 조건은 decision_year, decision_month, decision_day를 사용하세요
7. 업권, 조치유형 등의 텍스트는 LIKE '%keyword%' 형식으로 검색하세요
8. 가능한 한 JOIN을 활용해 관련 정보를 함께 조회하세요
9. 결과는 최신순으로 정렬하세요

쿼리 유형을 다음 중에서 선택하세요:
- specific_target: 특정 대상 조회
- violation_type: 위반 유형별 조회  
- action_level: 조치 수준별 조회
- time_based: 시간 기반 조회
- statistics: 통계 분석
- complex_condition: 복합 조건 조회

응답 형식:
{{
    "query_type": "쿼리 유형",
    "sql": "생성된 SQL 쿼리",
    "description": "쿼리 설명"
}}
"""
    
    async def process_natural_query(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """자연어 쿼리를 SQL로 변환하고 실행"""
        try:
            # 1. AI를 통한 SQL 생성
            prompt = self.create_nl2sql_prompt(query)
            # 직접 API 호출 (V2 테이블용)
            ai_response = await self.gemini_service._make_api_request_with_rate_limit(prompt)
            
            # 2. 응답 파싱
            parsed_response = self.parse_ai_response(ai_response)
            if not parsed_response:
                return {
                    'success': False,
                    'error': 'AI 응답 파싱 실패'
                }
            
            # 3. SQL 실행
            sql_query = parsed_response['sql']
            
            # 세미콜론 제거 및 LIMIT 처리
            sql_query = sql_query.strip().rstrip(';')
            
            # LIMIT 추가 (이미 있으면 추가하지 않음)
            if 'LIMIT' not in sql_query.upper():
                sql_query = f"{sql_query} LIMIT {limit}"
            
            logger.info(f"생성된 SQL (V2): {sql_query}")
            
            # 4. 쿼리 실행
            result = self.db.execute(text(sql_query))
            rows = result.fetchall()
            
            # 5. 결과 포맷팅
            formatted_results = self.format_results(rows, result.keys())
            
            return {
                'success': True,
                'query_type': parsed_response.get('query_type', 'unknown'),
                'sql_query': sql_query,
                'results': formatted_results,
                'metadata': {
                    'description': parsed_response.get('description', ''),
                    'total_results': len(formatted_results)
                }
            }
            
        except Exception as e:
            logger.error(f"NL2SQL 처리 오류 (V2): {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def parse_ai_response(self, response: str) -> Dict[str, Any]:
        """AI 응답 파싱"""
        try:
            # JSON 블록 추출
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            
            # 단순 SQL 쿼리만 있는 경우
            sql_match = re.search(r'SELECT[\s\S]+?(?:;|$)', response, re.IGNORECASE)
            if sql_match:
                return {
                    'sql': sql_match.group().strip().rstrip(';'),
                    'query_type': 'unknown',
                    'description': ''
                }
            
            return None
            
        except Exception as e:
            logger.error(f"AI 응답 파싱 오류: {e}")
            return None
    
    def format_results(self, rows: List, columns: List[str]) -> List[Dict[str, Any]]:
        """쿼리 결과를 딕셔너리 리스트로 포맷팅"""
        formatted = []
        
        for row in rows:
            result_dict = {}
            for i, col in enumerate(columns):
                value = row[i]
                # None 값 처리
                if value is None:
                    result_dict[col] = None
                # 날짜 형식 처리
                elif hasattr(value, 'isoformat'):
                    result_dict[col] = value.isoformat()
                else:
                    result_dict[col] = value
            
            # 필수 필드 확인 및 기본값 설정
            if 'decision_id' not in result_dict and 'decision_pk' in result_dict:
                # decision_pk만 있는 경우 처리
                result_dict['decision_id'] = result_dict.get('decision_pk')
            
            if 'decision_year' not in result_dict:
                result_dict['decision_year'] = None
            
            # 법률 정보 추가 (action_id가 있는 경우)
            if 'action_id' in result_dict and result_dict['action_id']:
                action_id = result_dict['action_id']
                laws = self.db.query(
                    LawV2.law_name, 
                    ActionLawMapV2.article_details
                ).join(
                    ActionLawMapV2, 
                    ActionLawMapV2.law_id == LawV2.law_id
                ).filter(
                    ActionLawMapV2.action_id == action_id
                ).all()
                
                result_dict['laws'] = [
                    {'law_name': law.law_name, 'article_details': law.article_details}
                    for law in laws
                ]
                
            formatted.append(result_dict)
        
        return formatted
    
    def get_sample_queries(self) -> List[str]:
        """V2용 샘플 쿼리"""
        return [
            "2025년에 발행된 모든 의결서를 보여주세요",
            "과태료가 1억원 이상인 제재 사례를 찾아주세요",
            "자산운용사에 대한 제재 현황을 알려주세요",
            "최근 10건의 의결서를 보여주세요",
            "직무정지 처분을 받은 사례를 검색해주세요",
            "자본시장법 위반 사례를 찾아주세요",
            "월별 제재 건수 통계를 보여주세요",
            "가장 높은 과징금을 받은 기관은 어디인가요?",
            "회계 관련 위반 사례를 찾아주세요",
            "업권별 제재 건수를 비교해주세요"
        ]