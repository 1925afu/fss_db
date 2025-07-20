"""
Gemini Structured Output 서비스
Pydantic 모델과 response_schema를 활용한 구조화된 데이터 추출
"""
import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any, Type
from datetime import datetime
import google.generativeai as genai
from pydantic import BaseModel, ValidationError
from app.models.pydantic_models import Decision, Action, ActionLawMap
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiStructuredService:
    """Gemini API를 사용한 구조화된 데이터 추출 서비스"""
    
    def __init__(self):
        # API 키 설정
        api_key = os.getenv("GOOGLE_API_KEY") or settings.GOOGLE_API_KEY
        if not api_key:
            raise ValueError("GOOGLE_API_KEY가 설정되지 않았습니다.")
        
        genai.configure(api_key=api_key)
        
        # 모델 설정 (Structured Output 지원 버전)
        model_name = settings.GEMINI_MODEL or "gemini-2.0-flash-exp"
        logger.info(f"Using Gemini model: {model_name}")
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": 0.1,  # 낮은 온도로 일관성 향상
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )
        
        # Rate limiting 설정
        self.rate_limit_delay = 6  # 분당 10회 제한 (6초 간격)
        self.last_request_time = None
        
    async def extract_decision_data(
        self, 
        pdf_text: str, 
        metadata: Dict[str, Any]
    ) -> Decision:
        """PDF 텍스트에서 의결서 데이터를 구조화하여 추출"""
        try:
            # Rate limiting
            await self._apply_rate_limit()
            
            # 프롬프트 생성
            prompt = self._create_extraction_prompt(pdf_text, metadata)
            
            # Gemini API용 간소화된 스키마 생성
            decision_schema = self._create_simplified_schema()
            
            # Structured Output 설정
            generation_config = genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=decision_schema,  # 간소화된 스키마 사용
                temperature=0.1,
            )
            
            # API 호출
            logger.info(f"Gemini API 호출 시작 - 파일: {metadata.get('filename', 'unknown')}")
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # 응답 파싱
            if response.text:
                # JSON 응답을 Pydantic 모델로 변환
                decision_data = json.loads(response.text)
                decision = Decision(**decision_data)
                
                logger.info(f"구조화된 데이터 추출 성공 - 조치 수: {len(decision.actions)}")
                return decision
            else:
                raise Exception("Gemini API 응답이 비어있습니다.")
                
        except ValidationError as e:
            logger.error(f"Pydantic 검증 실패: {e}")
            raise
        except Exception as e:
            logger.error(f"구조화된 데이터 추출 실패: {e}")
            raise
    
    def _create_extraction_prompt(self, pdf_text: str, metadata: Dict[str, Any]) -> str:
        """데이터 추출을 위한 프롬프트 생성"""
        prompt = f"""당신은 금융위원회 의결서 분석 전문가입니다. 
주어진 PDF 텍스트에서 제재 및 조치 정보를 정확하게 추출하여 구조화된 형식으로 반환해주세요.

=== 메타데이터 ===
파일명: {metadata.get('filename', '')}
추출된 연도: {metadata.get('year', '')}
추출된 의결번호: {metadata.get('decision_id', '')}

=== PDF 텍스트 ===
{pdf_text}

=== 추출 지침 ===
1. 의결서 정보:
   - decision_year: 의결서 연도 (메타데이터 참조)
   - decision_id: 의결서 호수 (메타데이터 참조)
   - title: 의결서 제목 (전체)
   - submitter: 의안 제출자 (주로 "금융감독원")
   - category_1: 대분류 (제재/인허가/정책 중 선택)
   - category_2: 중분류 (기관/임직원/전문가/기타 중 선택)

2. 조치(Action) 정보:
   - 각 제재 대상별로 별도의 Action 객체 생성
   - entity_name: 정확한 기관명 또는 개인명
   - industry_sector: 업권 (은행/보험/금융투자/자산운용 등)
   - action_type: 조치 유형 (과태료, 직무정지, 기관경고 등)
   - fine_amount: 숫자로 변환 (100백만원 → 100000000)
   - violation_summary: 핵심 위반 내용을 간결하게 요약

3. 법률 정보:
   - law_name: 법률의 정식 명칭
   - article_details: 구체적인 조항 (예: "제85조 제8호")
   - article_purpose: 해당 조항의 내용 요약

4. 주의사항:
   - 모든 금액은 원 단위로 변환
   - 날짜는 YYYY-MM-DD 형식 사용
   - 법률명은 정식 명칭 사용 (약칭 X)
   - 조치가 여러 개인 경우 각각 별도의 Action으로 분리

응답은 반드시 지정된 JSON 스키마를 준수해야 합니다."""
        
        return prompt
    
    async def _apply_rate_limit(self):
        """Rate limiting 적용"""
        if self.last_request_time:
            elapsed = (datetime.now() - self.last_request_time).total_seconds()
            if elapsed < self.rate_limit_delay:
                wait_time = self.rate_limit_delay - elapsed
                logger.debug(f"Rate limiting: {wait_time:.1f}초 대기")
                await asyncio.sleep(wait_time)
        
        self.last_request_time = datetime.now()
    
    async def extract_with_retry(
        self, 
        pdf_text: str, 
        metadata: Dict[str, Any], 
        max_retries: int = 3
    ) -> Optional[Decision]:
        """재시도 로직을 포함한 데이터 추출"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"재시도 {attempt}/{max_retries}")
                    await asyncio.sleep(self.rate_limit_delay * (attempt + 1))
                
                decision = await self.extract_decision_data(pdf_text, metadata)
                return decision
                
            except Exception as e:
                logger.error(f"추출 시도 {attempt + 1} 실패: {e}")
                if attempt == max_retries - 1:
                    raise
        
        return None
    
    async def validate_extraction(self, decision: Decision, original_text: str) -> Dict[str, Any]:
        """추출된 데이터 검증"""
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 필수 필드 검증
        if not decision.decision_year or not decision.decision_id:
            validation_result['is_valid'] = False
            validation_result['errors'].append("의결서 기본 정보 누락")
        
        # 조치 정보 검증
        if not decision.actions:
            validation_result['warnings'].append("조치 정보가 없습니다")
        else:
            for i, action in enumerate(decision.actions):
                if not action.entity_name:
                    validation_result['errors'].append(f"조치 {i+1}: 대상 기관/개인명 누락")
                if not action.action_type:
                    validation_result['errors'].append(f"조치 {i+1}: 조치 유형 누락")
                if not action.action_law_map:
                    validation_result['warnings'].append(f"조치 {i+1}: 관련 법률 정보 없음")
        
        # 원문 대조 검증 (선택적)
        if decision.title and decision.title not in original_text:
            validation_result['warnings'].append("제목이 원문에서 찾을 수 없습니다")
        
        return validation_result
    
    def _create_simplified_schema(self) -> Dict[str, Any]:
        """Gemini API용 간소화된 스키마 생성"""
        # 복잡한 Pydantic 스키마 대신 직접 정의
        return {
            "type": "object",
            "properties": {
                "decision_year": {"type": "integer"},
                "decision_id": {"type": "integer"},
                "title": {"type": "string"},
                "submitter": {"type": "string"},
                "full_text": {"type": "string"},
                "agenda_no": {"type": "string"},
                "category_1": {"type": "string"},
                "category_2": {"type": "string"},
                "submission_date": {"type": "string"},
                "stated_purpose": {"type": "string"},
                "decision_month": {"type": "integer"},
                "decision_day": {"type": "integer"},
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "entity_name": {"type": "string"},
                            "industry_sector": {"type": "string"},
                            "violation_details": {"type": "string"},
                            "action_type": {"type": "string"},
                            "fine_amount": {"type": "integer"},
                            "violation_summary": {"type": "string"},
                            "target_details": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "position": {"type": "string"},
                                    "name": {"type": "string"}
                                }
                            },
                            "fine_basis_amount": {"type": "integer"},
                            "sanction_period": {"type": "string"},
                            "sanction_scope": {"type": "string"},
                            "effective_date": {"type": "string"},
                            "action_law_map": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "law_name": {"type": "string"},
                                        "article_details": {"type": "string"},
                                        "article_purpose": {"type": "string"}
                                    },
                                    "required": ["law_name", "article_details"]
                                }
                            }
                        },
                        "required": ["entity_name", "action_type", "violation_summary", "action_law_map"]
                    }
                }
            },
            "required": ["decision_year", "decision_id", "title", "full_text", "actions"]
        }
    
    def _remove_defaults_from_schema(self, schema: Dict[str, Any]) -> None:
        """JSON Schema에서 default 필드를 재귀적으로 제거"""
        if isinstance(schema, dict):
            # default 필드 제거
            if 'default' in schema:
                del schema['default']
            
            # properties 처리
            if 'properties' in schema:
                for prop in schema['properties'].values():
                    self._remove_defaults_from_schema(prop)
            
            # items 처리 (배열)
            if 'items' in schema:
                self._remove_defaults_from_schema(schema['items'])
            
            # definitions 처리
            if 'definitions' in schema:
                for definition in schema['definitions'].values():
                    self._remove_defaults_from_schema(definition)
            
            # $defs 처리 (JSON Schema Draft 2019-09+)
            if '$defs' in schema:
                for definition in schema['$defs'].values():
                    self._remove_defaults_from_schema(definition)
    
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        return {
            'model_name': self.model.model_name,
            'generation_config': self.model.generation_config,
            'rate_limit': f"{60 / self.rate_limit_delay:.1f} requests/min"
        }