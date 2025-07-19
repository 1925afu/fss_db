import google.generativeai as genai
from typing import Dict, Any, Optional
from app.core.config import settings
import json
import logging
import asyncio
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GeminiService:
    """Google Gemini API 서비스 (Rate Limiting 지원)"""
    
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        # 기본 모델 (PDF 처리, 데이터 추출 등)
        self.main_model = genai.GenerativeModel(settings.GEMINI_MODEL)
        # NL2SQL 전용 모델 (빠른 처리, 비용 효율성)
        self.nl2sql_model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")
        self.prompt_dir = settings.PROMPT_DIR
        self._load_prompts()
        
        # Rate limiting 설정 (Free tier: 분당 10회)
        self.rate_limit_requests_per_minute = 10
        self.rate_limit_window = 60  # 초
        self.request_timestamps = []
        self.max_retries = 5
        self.base_delay = 6  # 초 (60초 / 10회 = 6초)
    
    def _load_prompts(self):
        """프롬프트 파일들을 로드합니다."""
        try:
            # 기존 프롬프트 로드
            with open(f"{self.prompt_dir}/extractor_prompt.txt", 'r', encoding='utf-8') as f:
                self.extractor_prompt = f.read()
            
            with open(f"{self.prompt_dir}/validator_prompt.txt", 'r', encoding='utf-8') as f:
                self.validator_prompt = f.read()
            
            # Flash-Lite 최적화 프롬프트 우선 시도
            try:
                with open(f"{self.prompt_dir}/nl2sql_flash_lite_prompt.txt", 'r', encoding='utf-8') as f:
                    self.nl2sql_prompt = f.read()
            except FileNotFoundError:
                try:
                    with open(f"{self.prompt_dir}/nl2sql_prompt_v2.txt", 'r', encoding='utf-8') as f:
                        self.nl2sql_prompt = f.read()
                except FileNotFoundError:
                    with open(f"{self.prompt_dir}/nl2sql_prompt.txt", 'r', encoding='utf-8') as f:
                        self.nl2sql_prompt = f.read()

            # 2단계 파이프라인 프롬프트 로드
            with open(f"{self.prompt_dir}/analyzer_prompt.txt", 'r', encoding='utf-8') as f:
                self.analyzer_prompt = f.read()

            with open(f"{self.prompt_dir}/db_structuring_prompt.txt", 'r', encoding='utf-8') as f:
                self.db_structuring_prompt = f.read()
                
        except FileNotFoundError as e:
            logger.error(f"프롬프트 파일을 찾을 수 없습니다: {e}")
            # 기본 프롬프트 사용
            self.extractor_prompt = "PDF 내용을 분석하여 구조화된 JSON 데이터로 변환해주세요."
            self.validator_prompt = "추출된 데이터를 검증해주세요."
            self.nl2sql_prompt = "자연어 질문을 SQL 쿼리로 변환해주세요."
            self.analyzer_prompt = "문서의 구조를 분석하고 위반 사항을 논리적 그룹으로 묶어주세요."
            self.db_structuring_prompt = "분석된 데이터를 DB 스키마에 맞게 변환해주세요."
    
    def _check_rate_limit(self) -> float:
        """Rate limit을 확인하고 필요한 대기 시간을 반환합니다."""
        now = time.time()
        
        # 1분 이전의 요청들 제거
        self.request_timestamps = [
            timestamp for timestamp in self.request_timestamps 
            if now - timestamp < self.rate_limit_window
        ]
        
        # 현재 요청 수가 제한을 초과하는지 확인
        if len(self.request_timestamps) >= self.rate_limit_requests_per_minute:
            # 가장 오래된 요청 시간을 기준으로 대기 시간 계산
            oldest_request = min(self.request_timestamps)
            wait_time = self.rate_limit_window - (now - oldest_request) + 1  # 1초 버퍼
            return max(wait_time, 0)
        
        return 0
    
    def _record_request(self):
        """API 요청을 기록합니다."""
        self.request_timestamps.append(time.time())
    
    async def _make_api_request_with_rate_limit(self, prompt: str, model=None, retry_count: int = 0) -> str:
        """Rate limit을 고려하여 API 요청을 수행합니다."""
        try:
            # 모델 선택 (기본값: main_model)
            selected_model = model if model is not None else self.main_model
            
            # Rate limit 확인
            wait_time = self._check_rate_limit()
            if wait_time > 0:
                logger.info(f"Rate limit 대기: {wait_time:.1f}초")
                await asyncio.sleep(wait_time)
            
            # API 요청 기록
            self._record_request()
            
            # API 호출
            response = await selected_model.generate_content_async(prompt)
            return response.text.strip()
            
        except Exception as e:
            error_str = str(e)
            
            # Rate limit 에러 처리
            if "quota" in error_str.lower() or "rate" in error_str.lower() or "429" in error_str:
                if retry_count < self.max_retries:
                    # 지수 백오프로 대기 시간 증가
                    wait_time = self.base_delay * (2 ** retry_count)
                    logger.warning(f"Rate limit 에러 발생, {wait_time}초 후 재시도 ({retry_count + 1}/{self.max_retries}): {error_str}")
                    await asyncio.sleep(wait_time)
                    return await self._make_api_request_with_rate_limit(prompt, model, retry_count + 1)
                else:
                    logger.error(f"최대 재시도 횟수 초과, API 요청 실패: {error_str}")
                    raise Exception(f"Rate limit 에러로 인한 API 요청 실패: {error_str}")
            else:
                logger.error(f"API 요청 에러: {error_str}")
                raise

    async def extract_structured_data_2_step(self, pdf_content: str, pdf_filename: str = "") -> Dict[str, Any]:
        """2단계 파이프라인을 통해 PDF에서 구조화된 데이터를 추출합니다."""
        analysis_result_str = ""
        final_result_str = ""
        try:
            # --- Step 1: 분석 및 그룹핑 ---
            logger.info("2단계 추출 파이프라인 시작: 1단계 - 분석 및 그룹핑")
            step1_prompt = f"{self.analyzer_prompt}\n\n**문서 원본 텍스트:**\n{pdf_content}"
            
            analysis_result_str = await self._make_api_request_with_rate_limit(step1_prompt, model=self.main_model)

            if "```json" in analysis_result_str:
                analysis_json_str = analysis_result_str.split("```json")[1].split("```")[0].strip()
            else:
                analysis_json_str = analysis_result_str
            
            analysis_json = json.loads(analysis_json_str)
            logger.info("1단계 완료: 중간 분석 결과 생성 성공")

            # --- Step 2: DB 구조화 ---
            logger.info("2단계 추출 파이프라인 시작: 2단계 - DB 구조화")
            db_schema = self._get_db_schema()
            filename_info = f"\n\n**파일명:** {pdf_filename}" if pdf_filename else ""
            step2_prompt = f"{self.db_structuring_prompt}\n\n**DB 스키마:**\n{db_schema}{filename_info}\n\n**1단계 분석 결과 (JSON):**\n{json.dumps(analysis_json, ensure_ascii=False, indent=2)}"

            final_result_str = await self._make_api_request_with_rate_limit(step2_prompt, model=self.main_model)

            if "```json" in final_result_str:
                final_json_str = final_result_str.split("```json")[1].split("```")[0].strip()
            else:
                final_json_str = final_result_str

            final_json = json.loads(final_json_str)
            logger.info("2단계 완료: 최종 DB 구조화 JSON 생성 성공")
            
            return final_json

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            logger.error(f"1단계 결과 (문자열): {analysis_result_str}")
            logger.error(f"2단계 결과 (문자열): {final_result_str}")
            raise Exception(f"JSON 파싱 중 오류가 발생했습니다. AI 응답 형식을 확인하세요.")
        except Exception as e:
            logger.error(f"2단계 추출 파이프라인 중 오류 발생: {e}")
            raise

    def _get_db_schema(self) -> str:
        """데이터베이스 스키마 정보를 반환합니다."""
        return """
        데이터베이스 스키마:
        
        1. decisions (의결서)
        - decision_id (INTEGER, PK): 의안 ID
        - agenda_no (VARCHAR): 의안번호
        - decision_date (DATE): 의결일자
        - title (TEXT): 의안명
        - category_1 (VARCHAR): 대분류 (제재, 인허가, 정책)
        - category_2 (VARCHAR): 중분류 (기관, 임직원, 전문가, 정관변경, 법률개정)
        - submitter (VARCHAR): 제출자
        - submission_date (DATE): 제출일자
        - stated_purpose (TEXT): 제안이유/목적 요약
        - full_text (TEXT): 전문
        
        2. actions (조치)
        - action_id (INTEGER, PK): 조치 ID
        - decision_id (INTEGER, FK): 의안 ID
        - entity_name (VARCHAR): 대상 기관/개인명
        - industry_sector (VARCHAR): 업권 (은행, 보험, 금융투자, 회계/감사)
        - violation_details (TEXT): 위반/신청 내용
        - action_type (VARCHAR): 조치 유형 (과태료, 직무정지, 인가)
        - fine_amount (BIGINT): 과태료/과징금액
        - fine_basis_amount (BIGINT): 과태료 산정근거 금액
        - sanction_period (VARCHAR): 처분 기간
        - sanction_scope (TEXT): 처분 범위
        - effective_date (DATE): 조치 시행일
        
        3. laws (법규)
        - law_id (INTEGER, PK): 법규 ID
        - law_name (VARCHAR): 법률명
        - law_short_name (VARCHAR): 법률 약칭
        - law_category (VARCHAR): 법률 분류
        
        4. action_law_map (조치-법규 매핑)
        - map_id (INTEGER, PK): 매핑 ID
        - action_id (INTEGER, FK): 조치 ID
        - law_id (INTEGER, FK): 법규 ID
        - article_details (VARCHAR): 관련 조항
        - article_purpose (TEXT): 조항 내용 요약
        """
    
    async def convert_nl_to_sql(self, natural_query: str) -> str:
        """자연어 쿼리를 SQL로 변환합니다. (Flash-Lite 모델 사용)"""
        prompt = f"{self.nl2sql_prompt}\n\n{natural_query}"
        
        try:
            # NL2SQL 전용 모델 사용
            sql_query = await self._make_api_request_with_rate_limit(prompt, model=self.nl2sql_model)
            
            # SQL 쿼리에서 불필요한 텍스트 제거
            if "```sql" in sql_query:
                sql_query = sql_query.split("```sql")[1].split("```")[0].strip()
            elif "```" in sql_query:
                sql_query = sql_query.split("```")[1].strip()
            
            return sql_query
            
        except Exception as e:
            raise Exception(f"SQL 변환 중 오류 발생: {str(e)}")
    
    async def convert_nl_to_sql_advanced(self, natural_query: str, query_type: str = None) -> Dict[str, Any]:
        """고도화된 NL2SQL 변환 (AI 전용, Flash-Lite 모델)"""
        try:
            # 질의 유형별 프롬프트 선택
            if query_type:
                prompt = self._get_typed_nl2sql_prompt(natural_query, query_type)
            else:
                prompt = f"{self.nl2sql_prompt}\n\n사용자 질문: {natural_query}"
            
            # Flash-Lite 모델로 SQL 생성
            response = await self._make_api_request_with_rate_limit(prompt, model=self.nl2sql_model)
            
            # 구조화된 응답 파싱
            return self._parse_nl2sql_response(response)
            
        except Exception as e:
            logger.error(f"고도화된 NL2SQL 변환 실패: {e}")
            raise Exception(f"AI 기반 SQL 변환 중 오류 발생: {str(e)}")
    
    def _get_typed_nl2sql_prompt(self, query: str, query_type: str) -> str:
        """질의 유형별 최적화된 프롬프트 생성"""
        base_prompt = self.nl2sql_prompt
        
        type_specific_guidance = {
            "specific_target": "특정 회사명이나 개인명을 정확히 매칭하여 검색하세요.",
            "violation_type": "위반 행위 내용을 semantic하게 분석하여 관련 사례를 찾으세요.",
            "action_level": "조치 유형과 금액 조건을 정확히 파싱하여 필터링하세요.",
            "time_based": "복잡한 날짜 조건을 정확히 SQL로 변환하세요.",
            "complex_condition": "여러 조건을 논리적으로 조합하여 정확한 결과를 도출하세요.",
            "statistics": "집계 함수와 정렬을 활용하여 통계 분석 쿼리를 생성하세요."
        }
        
        guidance = type_specific_guidance.get(query_type, "")
        return f"{base_prompt}\n\n특별 지침: {guidance}\n\n사용자 질문: {query}"
    
    def _parse_nl2sql_response(self, response: str) -> Dict[str, Any]:
        """AI 응답을 구조화된 형태로 파싱"""
        try:
            # SQL 추출
            sql_query = ""
            if "```sql" in response:
                sql_query = response.split("```sql")[1].split("```")[0].strip()
            elif "```" in response:
                sql_query = response.split("```")[1].strip()
            else:
                # SQL 블록이 없으면 전체를 SQL로 간주
                sql_query = response.strip()
            
            return {
                "success": True,
                "sql_query": sql_query,
                "explanation": response,
                "model_used": "gemini-2.5-flash-lite-preview-06-17"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "raw_response": response
            }
    
    async def extract_structured_data(self, pdf_content: str, focused_extraction: Dict[str, Any] = None) -> Dict[str, Any]:
        """(기존 단일 단계) PDF 내용에서 구조화된 데이터를 추출합니다."""
        if focused_extraction:
            # 특정 오류에 집중한 맞춤 프롬프트 생성
            prompt = self._create_focused_prompt(pdf_content, focused_extraction)
        else:
            prompt = f"{self.extractor_prompt}\n\n{pdf_content}"
        
        try:
            result = await self._make_api_request_with_rate_limit(prompt, model=self.main_model)
            
            # JSON 추출
            if "```json" in result:
                json_str = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                json_str = result.split("```")[1].strip()
            else:
                json_str = result
            
            return json.loads(json_str)
            
        except Exception as e:
            raise Exception(f"PDF 데이터 추출 중 오류 발생: {str(e)}")
    
    def _create_focused_prompt(self, pdf_content: str, focused_extraction: Dict[str, Any]) -> str:
        """검증 오류에 따른 맞춤 프롬프트를 생성합니다."""
        missing_fields = focused_extraction.get('missing_fields', [])
        error_types = focused_extraction.get('error_types', [])
        
        focus_instructions = []
        
        # 누락된 필드별 집중 지침
        if '법률' in ' '.join(missing_fields):
            focus_instructions.append("- 문서에서 언급된 모든 법률명과 조항을 주의깊게 찾아서 추출하세요.")
        
        if '업권' in ' '.join(missing_fields):
            focus_instructions.append("- 대상 기관의 업권(은행, 보험, 금융투자, 회계/감사)을 명확히 식별하세요.")
        
        if 'agenda_no' in missing_fields:
            focus_instructions.append("- 의안번호에서 숫자만 추출하세요 (예: '제476호' → 476).")
        
        if '시행일자' in ' '.join(missing_fields):
            focus_instructions.append("- 조치의 시행일자나 효력 발생일을 찾아서 추출하세요.")
        
        focused_prompt = f"""
다음 FSC 의결서에서 특히 아래 항목들을 집중적으로 추출해주세요:

**집중 추출 항목:**
{chr(10).join(focus_instructions)}

**기본 추출 형식:**
{self.extractor_prompt}

**문서 내용:**
{pdf_content}
"""
        
        return focused_prompt
    
    def analyze_validation_errors(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """검증 오류를 분석하여 재처리 정보를 생성합니다."""
        errors = validation_result.get('errors', [])
        
        missing_fields = []
        error_types = []
        
        for error in errors:
            # 오류 형태 확인 및 처리
            if isinstance(error, dict):
                # 새로운 구조화된 오류 형태 처리
                error_message = error.get('message', '')
                error_field = error.get('field', '')
                error_code = error.get('code', '')
                
                # 필드 기반 분석
                if 'actions.industry_sector' in error_field or 'industry_sector' in error_field:
                    missing_fields.append('업권')
                    error_types.append('missing_industry')
                
                if 'legal_basis' in error_field or 'law' in error_field:
                    missing_fields.append('법률')
                    error_types.append('missing_law')
                
                if 'agenda_no' in error_field:
                    missing_fields.append('agenda_no')
                    error_types.append('incorrect_format')
                
                # 메시지 기반 분석
                error_lower = error_message.lower()
                
            else:
                # 기존 문자열 오류 형태 처리
                error_message = str(error)
                error_lower = error_message.lower()
            
            # 공통 메시지 분석
            if '법률' in error_message or 'law' in error_lower:
                if '법률' not in missing_fields:
                    missing_fields.append('법률')
                    error_types.append('missing_law')
            
            if '업권' in error_message or '분류' in error_message:
                if '업권' not in missing_fields:
                    missing_fields.append('업권')
                    error_types.append('missing_industry')
            
            if 'agenda_no' in error_message or '의안번호' in error_message:
                if 'agenda_no' not in missing_fields:
                    missing_fields.append('agenda_no')
                    error_types.append('incorrect_format')
            
            if '시행일자' in error_message or 'enforcement_date' in error_message:
                if '시행일자' not in missing_fields:
                    missing_fields.append('시행일자')
                    error_types.append('missing_date')
        
        return {
            'missing_fields': missing_fields,
            'error_types': error_types,
            'should_retry': len(missing_fields) > 0
        }
    
    async def validate_extracted_data(self, extracted_data: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """추출된 데이터의 유효성을 검증합니다."""
        prompt = f"{self.validator_prompt}\n\n**원본 텍스트:**\n{original_text}\n\n**추출된 데이터:**\n{json.dumps(extracted_data, ensure_ascii=False, indent=2)}"
        
        try:
            result = await self._make_api_request_with_rate_limit(prompt, model=self.main_model)
            
            # JSON 추출
            if "```json" in result:
                json_str = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                json_str = result.split("```")[1].strip()
            else:
                json_str = result
            
            return json.loads(json_str)
            
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"검증 중 오류 발생: {str(e)}"],
                "corrections": {},
                "confidence_score": 0.0
            }
    
    async def summarize_violation_content(self, violation_full_text: str) -> str:
        """위반 내용 전문을 AI로 요약합니다."""
        if not violation_full_text.strip():
            return ""
        
        prompt = f"""
다음은 금융감독원 의결서의 '조치 이유' 섹션 내용입니다. 이를 핵심 위반 내용으로 간단명료하게 요약해주세요.

**요약 지침:**
1. 위반 행위의 핵심만 2-3문장으로 요약
2. 법적 근거나 절차적 설명은 제외
3. 구체적인 위반 사실과 결과에 집중
4. 한국어로 작성

**원문:**
{violation_full_text}

**요약 결과 (2-3문장):**
"""
        
        try:
            summary = await self._make_api_request_with_rate_limit(prompt, model=self.main_model)
            
            logger.info(f"위반 내용 요약 완료: {len(summary)}자")
            return summary
            
        except Exception as e:
            logger.error(f"위반 내용 요약 실패: {e}")
            return ""
    
    async def extract_target_details_ai(self, text: str, rule_based_targets: Dict[str, Any]) -> Dict[str, Any]:
        """조치대상자 세부 정보를 AI로 추출하여 Rule-based 결과를 보완합니다."""
        
        prompt = f"""
다음 금융감독원 의결서에서 조치대상자의 세부 정보를 추출해주세요.

**기존 Rule-based 추출 결과:**
{json.dumps(rule_based_targets, ensure_ascii=False, indent=2)}

**추가로 추출할 정보:**
1. 개인 대상자의 경우: 정확한 직책, 성명 (익명화된 경우 그대로)
2. 회사/기관의 경우: 정확한 회사명
3. 외부감사인의 경우: 소속 회계법인명

**문서 내용:**
{text}

**JSON 형식으로 결과 출력:**
{{
    "target_type": "기관/임직원/외부감사인",
    "targets": [
        {{
            "type": "대상자 유형",
            "description": "전체 설명",
            "company": "회사명 (해당시)",
            "position": "직책 (해당시)",
            "name": "성명 (해당시)",
            "firm": "소속 법인 (외부감사인의 경우)"
        }}
    ]
}}
"""
        
        try:
            result = await self._make_api_request_with_rate_limit(prompt, model=self.main_model)
            
            # JSON 추출
            if "```json" in result:
                json_str = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                json_str = result.split("```")[1].strip()
            else:
                json_str = result
            
            enhanced_targets = json.loads(json_str)
            logger.info(f"AI 조치대상자 세부 정보 추출 완료: {enhanced_targets}")
            return enhanced_targets
            
        except Exception as e:
            logger.error(f"AI 조치대상자 추출 실패: {e}")
            return rule_based_targets  # 실패 시 기존 결과 반환
    
    async def classify_categories_ai(self, text: str, filename: str) -> Dict[str, str]:
        """AI를 사용하여 카테고리를 자동 분류합니다."""
        
        prompt = f"""
다음 금융감독원 의결서의 내용과 파일명을 보고 카테고리를 분류해주세요.

**분류 기준:**

**category_1 (대분류):**
- "제재": 과태료, 과징금, 직무정지, 업무정지 등 처벌성 조치
- "인허가": 인가, 승인, 허가, 등록, 변경승인 등
- "정책": 법령 개정, 규정 제정, 정책 수립 등

**category_2 (중분류):**
- "기관": 금융기관 대상 조치
- "임직원": 개인 임직원 대상 조치  
- "전문가": 회계사, 감사인 등 전문가 대상 조치
- "정관변경": 정관 변경 관련
- "법률개정": 법령, 규정 개정 관련

**파일명:** {filename}

**문서 내용:**
{text[:1000]}...

**JSON 형식으로 결과 출력:**
{{
    "category_1": "제재/인허가/정책 중 하나",
    "category_2": "기관/임직원/전문가/정관변경/법률개정 중 하나"
}}
"""
        
        try:
            result = await self._make_api_request_with_rate_limit(prompt, model=self.main_model)
            
            # JSON 추출
            if "```json" in result:
                json_str = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                json_str = result.split("```")[1].strip()
            else:
                json_str = result
            
            categories = json.loads(json_str)
            logger.info(f"AI 카테고리 분류 완료: {categories}")
            return categories
            
        except Exception as e:
            logger.error(f"AI 카테고리 분류 실패: {e}")
            return {"category_1": "제재", "category_2": "기관"}  # 기본값