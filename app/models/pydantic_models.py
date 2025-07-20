"""
Pydantic models for Gemini Structured Output
리팩토링된 데이터 추출을 위한 스키마 정의
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime


# M:N 관계를 위한 중간 테이블 모델
class ActionLawMap(BaseModel):
    """조치와 법률 간의 매핑 정보"""
    law_name: str = Field(
        description="관련 법규의 전체 이름 (예: 자본시장과 금융투자업에 관한 법률)"
    )
    article_details: str = Field(
        description="관련 법 조항 (예: 제85조 제8호)"
    )
    article_purpose: Optional[str] = Field(
        default=None, 
        description="해당 조항의 목적 또는 내용 요약"
    )


# 조치(Action) 모델
class Action(BaseModel):
    """개별 조치 사항 정보"""
    entity_name: str = Field(
        description="제재 대상이 되는 기관명 또는 개인의 이름 (예: 타이거자산운용, 대표이사 甲)"
    )
    industry_sector: Optional[str] = Field(
        default=None, 
        description="대상 기관의 산업 분야 (예: 자산운용, 은행, 보험)"
    )
    violation_details: Optional[str] = Field(
        default=None, 
        description="위반 내용에 대한 상세 설명"
    )
    action_type: str = Field(
        description="제재/조치의 종류 (예: 과태료, 직무정지, 기관경고). 여러 개일 경우 쉼표로 구분"
    )
    fine_amount: Optional[int] = Field(
        default=None, 
        description="과태료 또는 과징금 금액. '백만원' 단위를 숫자로 변환 (예: 100백만원 -> 100000000)"
    )
    violation_summary: str = Field(
        description="AI가 요약한 핵심 위반 내용"
    )
    target_details: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="제재 대상에 대한 추가 정보 (예: {'type': '임직원', 'position': '대표이사'})"
    )
    action_law_map: List[ActionLawMap] = Field(
        description="해당 조치와 관련된 법규 목록"
    )
    
    # 추가 필드들 (기존 시스템 호환)
    fine_basis_amount: Optional[int] = Field(
        default=None,
        description="과태료 산정근거 금액"
    )
    sanction_period: Optional[str] = Field(
        default=None,
        description="처분 기간 (예: 3개월, 6개월)"
    )
    sanction_scope: Optional[str] = Field(
        default=None,
        description="처분 범위"
    )
    effective_date: Optional[str] = Field(
        default=None,
        description="조치 시행일 (YYYY-MM-DD 형식)"
    )


# 최상위 의결서(Decision) 모델
class Decision(BaseModel):
    """금융위원회 의결서 전체 정보"""
    decision_year: int = Field(
        description="의결서의 연도 (예: 2025)"
    )
    decision_id: int = Field(
        description="의결서의 호(ID) (예: 1)"
    )
    title: str = Field(
        description="의결서의 전체 제목"
    )
    submitter: Optional[str] = Field(
        default=None, 
        description="의안 제출자 (예: 금융감독원)"
    )
    full_text: str = Field(
        description="OCR로 추출한 의결서 원문 전체"
    )
    actions: List[Action] = Field(
        description="의결서에 포함된 모든 조치 사항 목록"
    )
    
    # 추가 필드들 (기존 시스템 호환)
    agenda_no: Optional[str] = Field(
        default=None,
        description="의안번호 (예: 제 200 호)"
    )
    category_1: Optional[str] = Field(
        default=None,
        description="대분류 (예: 제재, 인허가, 정책)"
    )
    category_2: Optional[str] = Field(
        default=None,
        description="중분류 (예: 기관, 임직원, 전문가)"
    )
    submission_date: Optional[str] = Field(
        default=None,
        description="제출일자 (YYYY-MM-DD 형식)"
    )
    stated_purpose: Optional[str] = Field(
        default=None,
        description="제안이유"
    )
    
    # 날짜 정보 (나중에 의결*.pdf에서 추출)
    decision_month: Optional[int] = Field(
        default=None,
        description="의결 월 (의결*.pdf에서 추출)"
    )
    decision_day: Optional[int] = Field(
        default=None,
        description="의결 일 (의결*.pdf에서 추출)"
    )


# NL2SQL을 위한 추가 모델들 (향후 확장용)
class NL2SQLQuery(BaseModel):
    """자연어 쿼리를 SQL로 변환하기 위한 모델"""
    natural_query: str = Field(
        description="사용자의 자연어 질문"
    )
    sql_query: str = Field(
        description="변환된 SQL 쿼리"
    )
    explanation: str = Field(
        description="쿼리 설명"
    )
    

class SearchResult(BaseModel):
    """검색 결과 모델"""
    decisions: List[Dict[str, Any]] = Field(
        description="검색된 의결서 목록"
    )
    total_count: int = Field(
        description="전체 결과 수"
    )
    query_info: Dict[str, Any] = Field(
        description="쿼리 정보"
    )