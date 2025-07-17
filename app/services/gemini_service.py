import google.generativeai as genai
from typing import Dict, Any, Optional
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)


class GeminiService:
    """Google Gemini API 서비스"""
    
    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        self.prompt_dir = settings.PROMPT_DIR
        self._load_prompts()
    
    def _load_prompts(self):
        """프롬프트 파일들을 로드합니다."""
        try:
            # 기존 프롬프트 로드
            with open(f"{self.prompt_dir}/extractor_prompt.txt", 'r', encoding='utf-8') as f:
                self.extractor_prompt = f.read()
            
            with open(f"{self.prompt_dir}/validator_prompt.txt", 'r', encoding='utf-8') as f:
                self.validator_prompt = f.read()
            
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

    async def extract_structured_data_2_step(self, pdf_content: str, pdf_filename: str = "") -> Dict[str, Any]:
        """2단계 파이프라인을 통해 PDF에서 구조화된 데이터를 추출합니다."""
        analysis_result_str = ""
        final_result_str = ""
        try:
            # --- Step 1: 분석 및 그룹핑 ---
            logger.info("2단계 추출 파이프라인 시작: 1단계 - 분석 및 그룹핑")
            step1_prompt = f"{self.analyzer_prompt}\n\n**문서 원본 텍스트:**\n{pdf_content}"
            
            response_step1 = await self.model.generate_content_async(step1_prompt)
            analysis_result_str = response_step1.text.strip()

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

            response_step2 = await self.model.generate_content_async(step2_prompt)
            final_result_str = response_step2.text.strip()

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
        """자연어 쿼리를 SQL로 변환합니다."""
        prompt = f"{self.nl2sql_prompt}\n\n{natural_query}"
        
        try:
            response = await self.model.generate_content_async(prompt)
            sql_query = response.text.strip()
            
            # SQL 쿼리에서 불필요한 텍스트 제거
            if "```sql" in sql_query:
                sql_query = sql_query.split("```sql")[1].split("```")[0].strip()
            elif "```" in sql_query:
                sql_query = sql_query.split("```")[1].strip()
            
            return sql_query
            
        except Exception as e:
            raise Exception(f"SQL 변환 중 오류 발생: {str(e)}")
    
    async def extract_structured_data(self, pdf_content: str, focused_extraction: Dict[str, Any] = None) -> Dict[str, Any]:
        """(기존 단일 단계) PDF 내용에서 구조화된 데이터를 추출합니다."""
        if focused_extraction:
            # 특정 오류에 집중한 맞춤 프롬프트 생성
            prompt = self._create_focused_prompt(pdf_content, focused_extraction)
        else:
            prompt = f"{self.extractor_prompt}\n\n{pdf_content}"
        
        try:
            response = await self.model.generate_content_async(prompt)
            result = response.text.strip()
            
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
            response = await self.model.generate_content_async(prompt)
            result = response.text.strip()
            
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