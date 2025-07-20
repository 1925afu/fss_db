"""
리팩토링된 FSC 데이터베이스 모델 (v2)
- Surrogate Key 사용 (decision_pk)
- 정규화된 법률 테이블
- 기존 복합키는 UNIQUE 제약조건으로 유지
"""
from sqlalchemy import Column, Integer, String, Text, Date, BigInteger, ForeignKey, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class DecisionV2(Base):
    """의결서 테이블 V2 - Surrogate Key 사용"""
    __tablename__ = "decisions_v2"
    
    # Surrogate Primary Key
    decision_pk = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # 기존 복합키는 UNIQUE 제약조건으로
    decision_year = Column(Integer, nullable=False, index=True)
    decision_id = Column(Integer, nullable=False, index=True)
    
    # 날짜 정보 분해 (의결*.pdf에서 추출)
    decision_month = Column(Integer, nullable=True)
    decision_day = Column(Integer, nullable=True)
    
    # 기본 필드들
    agenda_no = Column(String(50), nullable=True, index=True)
    title = Column(Text, nullable=False)
    category_1 = Column(String(50), nullable=True, index=True)  # 대분류
    category_2 = Column(String(50), nullable=True, index=True)  # 중분류
    submitter = Column(String(100), nullable=True)
    submission_date = Column(Date, nullable=True)
    stated_purpose = Column(Text, nullable=True)
    full_text = Column(Text, nullable=False)  # 전체 텍스트 (검색용)
    
    # 메타데이터
    source_file = Column(String(255), nullable=True)  # 원본 파일명
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    extra_metadata = Column(JSON, nullable=True)  # 추가 메타데이터
    
    # 관계 설정
    actions = relationship("ActionV2", back_populates="decision", cascade="all, delete-orphan")
    
    # 복합키 UNIQUE 제약조건
    __table_args__ = (
        UniqueConstraint('decision_year', 'decision_id', name='uq_decision_year_id'),
        Index('idx_decision_date', 'decision_year', 'decision_month', 'decision_day'),
    )
    
    @property
    def decision_date(self):
        """기존 코드 호환성을 위한 date 프로퍼티"""
        from datetime import date
        if self.decision_month and self.decision_day:
            try:
                return date(self.decision_year, self.decision_month, self.decision_day)
            except ValueError:
                return None
        return None


class ActionV2(Base):
    """조치 테이블 V2"""
    __tablename__ = "actions_v2"
    
    action_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # Foreign Key to Decision (Surrogate Key 참조)
    decision_pk = Column(Integer, ForeignKey("decisions_v2.decision_pk"), nullable=False)
    
    # 조치 대상 정보
    entity_name = Column(String(255), nullable=False, index=True)  # 대상 기관/개인명
    industry_sector = Column(String(50), nullable=True, index=True)  # 업권
    
    # 위반 정보
    violation_details = Column(Text, nullable=True)  # 위반 내용 상세
    violation_summary = Column(Text, nullable=False)  # AI 요약된 위반 내용
    
    # 조치 정보
    action_type = Column(String(100), nullable=False, index=True)  # 조치 유형 (쉼표 구분 가능)
    fine_amount = Column(BigInteger, nullable=True)  # 과태료/과징금액
    fine_basis_amount = Column(BigInteger, nullable=True)  # 과태료 산정근거 금액
    sanction_period = Column(String(50), nullable=True)  # 처분 기간
    sanction_scope = Column(Text, nullable=True)  # 처분 범위
    effective_date = Column(Date, nullable=True)  # 조치 시행일
    
    # 추가 정보
    target_details = Column(JSON, nullable=True)  # 조치대상자 세부 정보 (JSON)
    
    # 메타데이터
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    extra_metadata = Column(JSON, nullable=True)
    
    # 관계 설정
    decision = relationship("DecisionV2", back_populates="actions")
    law_mappings = relationship("ActionLawMapV2", back_populates="action", cascade="all, delete-orphan")


class LawV2(Base):
    """정규화된 법률 테이블 V2"""
    __tablename__ = "laws_v2"
    
    law_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    law_name = Column(String(255), unique=True, nullable=False)  # 법률 정식명칭 (UNIQUE)
    law_short_name = Column(String(100), nullable=False, index=True)  # 법률 약칭
    law_type = Column(String(50), nullable=True, index=True)  # 법률/시행령/규정 구분
    law_category = Column(String(50), nullable=True, index=True)  # 법률 분류
    effective_date = Column(Date, nullable=True)  # 시행일
    
    # 메타데이터
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    extra_metadata = Column(JSON, nullable=True)
    
    # 관계 설정
    action_mappings = relationship("ActionLawMapV2", back_populates="law")


class ActionLawMapV2(Base):
    """조치-법규 매핑 테이블 V2"""
    __tablename__ = "action_law_map_v2"
    
    map_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    action_id = Column(Integer, ForeignKey("actions_v2.action_id"), nullable=False)
    law_id = Column(Integer, ForeignKey("laws_v2.law_id"), nullable=False)
    article_details = Column(String(100), nullable=False)  # 관련 조항
    article_purpose = Column(Text, nullable=True)  # 조항 내용 요약
    
    # 메타데이터
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    extra_metadata = Column(JSON, nullable=True)
    
    # 관계 설정
    action = relationship("ActionV2", back_populates="law_mappings")
    law = relationship("LawV2", back_populates="action_mappings")
    
    # 복합 인덱스 (조회 성능 향상)
    __table_args__ = (
        Index('idx_action_law', 'action_id', 'law_id'),
    )