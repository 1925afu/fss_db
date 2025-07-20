from sqlalchemy import Column, Integer, String, Text, Date, BigInteger, ForeignKey, DateTime, JSON, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Decision(Base):
    """의결서 테이블"""
    __tablename__ = "decisions"
    
    # 복합 Primary Key (연도 + 의결번호)
    decision_year = Column(Integer, nullable=False, primary_key=True, index=True)
    decision_id = Column(Integer, nullable=False, primary_key=True, index=True)
    
    # 날짜 정보 분해
    decision_month = Column(Integer, nullable=False, index=True)
    decision_day = Column(Integer, nullable=False, index=True)
    
    # 기존 필드들
    agenda_no = Column(String(50), nullable=False, index=True)
    title = Column(Text, nullable=False)
    category_1 = Column(String(50), nullable=False, index=True)  # 대분류
    category_2 = Column(String(50), nullable=False, index=True)  # 중분류
    submitter = Column(String(100))
    submission_date = Column(Date)
    stated_purpose = Column(Text)
    full_text = Column(Text)  # 전체 텍스트 (검색용)
    
    # 추가 메타데이터
    source_file = Column(String(255))  # 원본 파일명
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    extra_metadata = Column(JSON)  # 추가 메타데이터 저장
    
    # 관계 설정
    actions = relationship("Action", back_populates="decision")
    
    @property
    def decision_date(self):
        """기존 코드 호환성을 위한 date 프로퍼티"""
        from datetime import date
        # 날짜 정보가 없는 경우 None 반환
        if self.decision_month == 0 or self.decision_day == 0:
            return None
        return date(self.decision_year, self.decision_month, self.decision_day)
    
    @decision_date.setter
    def decision_date(self, value):
        """date 객체를 년/월/일로 분해"""
        self.decision_year = value.year
        self.decision_month = value.month
        self.decision_day = value.day


class Action(Base):
    """조치 테이블"""
    __tablename__ = "actions"
    
    action_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # 복합 Foreign Key 참조
    decision_year = Column(Integer, nullable=False)
    decision_id = Column(Integer, nullable=False)
    
    entity_name = Column(String(255), nullable=False, index=True)  # 대상 기관/개인명
    industry_sector = Column(String(50), nullable=False, index=True)  # 업권
    violation_details = Column(Text, nullable=False)  # 위반/신청 내용
    action_type = Column(String(50), nullable=False, index=True)  # 조치 유형
    fine_amount = Column(BigInteger)  # 과태료/과징금액
    fine_basis_amount = Column(BigInteger)  # 과태료 산정근거 금액
    sanction_period = Column(String(50))  # 처분 기간
    sanction_scope = Column(Text)  # 처분 범위
    effective_date = Column(Date)  # 조치 시행일
    
    # 하이브리드 추출을 위한 새로운 컬럼들
    violation_full_text = Column(Text)  # 조치 이유 전문 (가. 지적사항 섹션)
    violation_summary = Column(Text)    # AI 요약된 위반 내용
    target_details = Column(JSON)       # 조치대상자 세부 정보 (JSON 형태)
    
    # 추가 메타데이터
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    extra_metadata = Column(JSON)
    
    # 복합 Foreign Key 제약조건
    __table_args__ = (
        ForeignKeyConstraint(
            ['decision_year', 'decision_id'],
            ['decisions.decision_year', 'decisions.decision_id']
        ),
    )
    
    # 관계 설정
    decision = relationship("Decision", back_populates="actions")
    law_mappings = relationship("ActionLawMap", back_populates="action")


class Law(Base):
    """법규 테이블"""
    __tablename__ = "laws"
    
    law_id = Column(Integer, primary_key=True, index=True)
    law_name = Column(String(255), unique=True, nullable=False)  # 법률 정식명칭
    law_short_name = Column(String(100), nullable=False, index=True)  # 법률 약칭
    law_category = Column(String(50), nullable=False, index=True)  # 법률 분류
    
    # 추가 메타데이터
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    extra_metadata = Column(JSON)
    
    # 관계 설정
    action_mappings = relationship("ActionLawMap", back_populates="law")


class ActionLawMap(Base):
    """조치-법규 매핑 테이블"""
    __tablename__ = "action_law_map"
    
    map_id = Column(Integer, primary_key=True, index=True)
    action_id = Column(Integer, ForeignKey("actions.action_id"), nullable=False)
    law_id = Column(Integer, ForeignKey("laws.law_id"), nullable=False)
    article_details = Column(String(100), nullable=False)  # 관련 조항
    article_purpose = Column(Text)  # 조항 내용 요약
    
    # 추가 메타데이터
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    extra_metadata = Column(JSON)
    
    # 관계 설정
    action = relationship("Action", back_populates="law_mappings")
    law = relationship("Law", back_populates="action_mappings")