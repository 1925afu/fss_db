"""
PDF 처리 서비스 V2
Gemini Structured Output을 활용한 새로운 파이프라인
"""
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.preprocessing import PDFPreprocessor
from app.services.gemini_structured_service import GeminiStructuredService
from app.models.pydantic_models import Decision, Action, ActionLawMap
from app.models.fsc_models_v2 import DecisionV2, ActionV2, LawV2, ActionLawMapV2, Base
from app.core.config import settings

logger = logging.getLogger(__name__)


class PDFProcessorV2:
    """PDF 처리 서비스 V2 - Structured Output 기반"""
    
    def __init__(self, db_path: str = None):
        # 기존 데이터베이스 연결 사용
        from app.core.database import engine, SessionLocal
        from app.core.config import settings
        self.db_path = db_path or settings.DATABASE_URL
        self.engine = engine
        self.SessionLocal = SessionLocal
        
        # 테이블 생성 (없으면)
        Base.metadata.create_all(bind=self.engine)
        
        # 서비스 초기화
        self.preprocessor = PDFPreprocessor()
        self.gemini_service = GeminiStructuredService()
        
        # 디렉토리 설정
        self.processed_pdf_dir = settings.PROCESSED_PDF_DIR or "data/processed_pdf"
        
    async def process_single_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """단일 PDF 파일을 처리합니다."""
        session = self.SessionLocal()
        
        try:
            logger.info(f"PDF 처리 시작 (V2): {pdf_path}")
            
            # 1단계: 전처리
            logger.info("1단계: PDF 전처리")
            preprocessed_data = self.preprocessor.preprocess_pdf(pdf_path)
            
            # 2단계: Structured Output 추출
            logger.info("2단계: Gemini Structured Output 추출")
            decision_data = await self.gemini_service.extract_with_retry(
                preprocessed_data['markdown_text'],
                preprocessed_data['metadata']
            )
            
            if not decision_data:
                raise Exception("데이터 추출 실패")
            
            # 3단계: 데이터베이스 저장
            logger.info("3단계: 데이터베이스 저장")
            db_result = await self._save_to_database(session, decision_data, pdf_path)
            
            # 4단계: 실제 날짜 추출 (의결*.pdf에서)
            if db_result.get('decision'):
                await self._update_decision_date(session, db_result['decision'])
            
            session.commit()
            
            return {
                'success': True,
                'pdf_path': pdf_path,
                'decision_data': decision_data.model_dump(),
                'db_result': db_result,
                'processing_mode': 'structured_output'
            }
            
        except Exception as e:
            logger.error(f"PDF 처리 실패 (V2): {pdf_path} - {str(e)}")
            session.rollback()
            return {
                'success': False,
                'pdf_path': pdf_path,
                'error': str(e),
                'processing_mode': 'structured_output'
            }
        finally:
            session.close()
    
    async def _save_to_database(
        self, 
        session: Session, 
        decision_data: Decision, 
        pdf_path: str
    ) -> Dict[str, Any]:
        """추출된 데이터를 데이터베이스에 저장합니다."""
        try:
            # 기존 데이터 확인
            existing = session.query(DecisionV2).filter(
                DecisionV2.decision_year == decision_data.decision_year,
                DecisionV2.decision_id == decision_data.decision_id
            ).first()
            
            if existing:
                logger.warning(f"이미 존재하는 의결서: {decision_data.decision_year}-{decision_data.decision_id}")
                return {
                    'success': False,
                    'error': 'Already exists',
                    'decision': existing
                }
            
            # 의결서 생성
            decision = DecisionV2(
                decision_year=decision_data.decision_year,
                decision_id=decision_data.decision_id,
                decision_month=decision_data.decision_month or 1,  # 기본값
                decision_day=decision_data.decision_day or 1,      # 기본값
                agenda_no=decision_data.agenda_no,
                title=decision_data.title,
                category_1=decision_data.category_1,
                category_2=decision_data.category_2,
                submitter=decision_data.submitter,
                submission_date=self._parse_date(decision_data.submission_date),
                stated_purpose=decision_data.stated_purpose,
                full_text=decision_data.full_text,
                source_file=os.path.basename(pdf_path),
                extra_metadata={
                    'extracted_at': datetime.now().isoformat(),
                    'extractor_version': 'v2_structured_output'
                }
            )
            
            session.add(decision)
            session.flush()  # decision_pk 생성
            
            # 조치 데이터 저장
            actions_saved = []
            
            for action_data in decision_data.actions:
                action = await self._create_action(session, action_data, decision.decision_pk)
                if action:
                    actions_saved.append(action.action_id)
            
            logger.info(f"저장 완료: 의결서 {decision.decision_year}-{decision.decision_id}, 조치 {len(actions_saved)}건")
            
            return {
                'success': True,
                'decision': decision,
                'decision_year': decision.decision_year,
                'decision_id': decision.decision_id,
                'actions_saved': actions_saved
            }
            
        except Exception as e:
            logger.error(f"데이터베이스 저장 실패: {str(e)}")
            raise
    
    async def _create_action(
        self, 
        session: Session, 
        action_data: Action, 
        decision_pk: int
    ) -> Optional[ActionV2]:
        """조치 데이터를 생성합니다."""
        try:
            # Action 생성
            action = ActionV2(
                decision_pk=decision_pk,
                entity_name=action_data.entity_name,
                industry_sector=action_data.industry_sector,
                violation_details=action_data.violation_details,
                violation_summary=action_data.violation_summary,
                action_type=action_data.action_type,
                fine_amount=action_data.fine_amount,
                fine_basis_amount=action_data.fine_basis_amount,
                sanction_period=action_data.sanction_period,
                sanction_scope=action_data.sanction_scope,
                effective_date=self._parse_date(action_data.effective_date),
                target_details=action_data.target_details,
                extra_metadata={
                    'extracted_at': datetime.now().isoformat()
                }
            )
            
            session.add(action)
            session.flush()  # action_id 생성
            
            # 법률 매핑 처리
            for law_map in action_data.action_law_map:
                await self._create_law_mapping(session, action.action_id, law_map)
            
            return action
            
        except Exception as e:
            logger.error(f"조치 생성 실패: {str(e)}")
            return None
    
    async def _create_law_mapping(
        self, 
        session: Session, 
        action_id: int, 
        law_map: ActionLawMap
    ) -> Optional[ActionLawMapV2]:
        """법률 매핑을 생성합니다."""
        try:
            # 법률 조회/생성
            law = await self._get_or_create_law(session, law_map.law_name)
            
            if not law:
                logger.warning(f"법률 생성 실패: {law_map.law_name}")
                return None
            
            # 매핑 생성
            mapping = ActionLawMapV2(
                action_id=action_id,
                law_id=law.law_id,
                article_details=law_map.article_details,
                article_purpose=law_map.article_purpose
            )
            
            session.add(mapping)
            
            logger.debug(f"법률 매핑 생성: {law.law_name} - {law_map.article_details}")
            return mapping
            
        except Exception as e:
            logger.error(f"법률 매핑 생성 실패: {str(e)}")
            return None
    
    async def _get_or_create_law(self, session: Session, law_name: str) -> Optional[LawV2]:
        """법률을 조회하거나 생성합니다."""
        try:
            # 정규화
            normalized_name = self._normalize_law_name(law_name)
            
            # 기존 법률 조회
            existing = session.query(LawV2).filter(
                LawV2.law_name == normalized_name
            ).first()
            
            if existing:
                return existing
            
            # 매핑 테이블에서 표준 법률명 찾기
            from sqlalchemy import text
            result = session.execute(
                text("SELECT new_law_id FROM law_name_mapping WHERE old_law_name = :name"),
                {'name': law_name}
            ).fetchone()
            
            if result:
                # 표준 법률 사용
                return session.query(LawV2).filter(
                    LawV2.law_id == result[0]
                ).first()
            
            # 새 법률 생성 (표준화되지 않은 경우)
            logger.warning(f"표준화되지 않은 법률 추가: {law_name}")
            
            new_law = LawV2(
                law_name=normalized_name,
                law_short_name=self._extract_short_name(normalized_name),
                law_type=self._determine_law_type(normalized_name),
                law_category='기타',
                extra_metadata={
                    'original_name': law_name,
                    'created_from': 'extraction'
                }
            )
            
            session.add(new_law)
            session.flush()
            
            return new_law
            
        except Exception as e:
            logger.error(f"법률 조회/생성 실패: {str(e)}")
            return None
    
    def _normalize_law_name(self, law_name: str) -> str:
        """법률명을 정규화합니다."""
        # 연속된 공백 제거
        normalized = ' '.join(law_name.split())
        
        # 특수문자 정규화
        normalized = normalized.replace('ㆍ', '·')
        
        return normalized.strip()
    
    def _extract_short_name(self, law_name: str) -> str:
        """법률명에서 약칭을 추출합니다."""
        # 간단한 규칙 기반 추출
        if '(' in law_name and ')' in law_name:
            start = law_name.rfind('(')
            end = law_name.rfind(')')
            if start < end:
                return law_name[start+1:end]
        
        # 기본: 첫 4글자 + "법"
        words = law_name.split()
        if words:
            return words[0][:4] + "법"
        
        return law_name[:10]
    
    def _determine_law_type(self, law_name: str) -> str:
        """법률 유형을 결정합니다."""
        if '시행령' in law_name:
            return '대통령령'
        elif '시행규칙' in law_name:
            return '총리령'
        elif '규정' in law_name or '규칙' in law_name:
            return '규정'
        else:
            return '법률'
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """날짜 문자열을 파싱합니다."""
        if not date_str:
            return None
        
        try:
            # ISO 형식
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.split('T')[0]).date()
            
            # 다양한 형식 시도
            for fmt in ['%Y-%m-%d', '%Y.%m.%d', '%Y/%m/%d', '%Y년 %m월 %d일']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            
            return None
            
        except Exception:
            return None
    
    async def _update_decision_date(self, session: Session, decision: DecisionV2):
        """의결*.pdf 파일에서 실제 날짜를 추출하여 업데이트합니다."""
        try:
            import re
            
            # 연도별 디렉토리 확인
            year_dir = os.path.join(self.processed_pdf_dir, str(decision.decision_year))
            search_dir = year_dir if os.path.exists(year_dir) else self.processed_pdf_dir
            
            # 매칭 파일 찾기
            pattern = f'의결{decision.decision_id}\\.'
            
            for filename in os.listdir(search_dir):
                if re.match(pattern, filename) and filename.endswith('.pdf'):
                    pdf_path = os.path.join(search_dir, filename)
                    
                    # 텍스트 추출
                    text = self.preprocessor.extract_text_from_pdf(pdf_path)
                    
                    # 날짜 패턴 검색
                    date_patterns = [
                        r'의결\s*연월일\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})',
                        r'의결일\s*[:：]\s*(\d{4})[\.년]\s*(\d{1,2})[\.월]\s*(\d{1,2})',
                        r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일.*?의결',
                    ]
                    
                    for pattern in date_patterns:
                        match = re.search(pattern, text[:1000])
                        if match:
                            year = int(match.group(1))
                            month = int(match.group(2))
                            day = int(match.group(3))
                            
                            if year == decision.decision_year:
                                # SQLAlchemy 컬럼 값 업데이트
                                session.query(DecisionV2).filter(
                                    DecisionV2.decision_pk == decision.decision_pk
                                ).update({
                                    'decision_month': month,
                                    'decision_day': day
                                })
                                logger.info(f"날짜 업데이트: {year}-{decision.decision_id} → {month}월 {day}일")
                                return
                    
                    break
            
        except Exception as e:
            logger.error(f"날짜 업데이트 실패: {e}")
    
    async def process_batch(
        self, 
        pdf_files: List[str], 
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """배치로 PDF 파일들을 처리합니다."""
        results = {
            'success': [],
            'failed': [],
            'total': len(pdf_files),
            'processed': 0
        }
        
        for i in range(0, len(pdf_files), batch_size):
            batch = pdf_files[i:i + batch_size]
            logger.info(f"배치 처리: {i+1}-{min(i+batch_size, len(pdf_files))}/{len(pdf_files)}")
            
            for pdf_file in batch:
                result = await self.process_single_pdf(pdf_file)
                
                if result['success']:
                    results['success'].append(result)
                else:
                    results['failed'].append(result)
                
                results['processed'] += 1
                
                # 진행상황 로그
                if results['processed'] % 10 == 0:
                    logger.info(f"진행률: {results['processed']}/{results['total']} "
                              f"(성공: {len(results['success'])}, 실패: {len(results['failed'])})")
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """처리 통계를 반환합니다."""
        session = self.SessionLocal()
        
        try:
            from sqlalchemy import func
            
            stats: Dict[str, Any] = {
                'total_decisions': session.query(DecisionV2).count(),
                'total_actions': session.query(ActionV2).count(),
                'total_laws': session.query(LawV2).count(),
                'total_law_mappings': session.query(ActionLawMapV2).count(),
            }
            
            # 연도별 통계
            year_stats = session.query(
                DecisionV2.decision_year,
                func.count(DecisionV2.decision_pk)
            ).group_by(DecisionV2.decision_year).all()
            
            stats['by_year'] = {year: count for year, count in year_stats}
            
            # 카테고리별 통계
            category_stats = session.query(
                DecisionV2.category_1,
                func.count(DecisionV2.decision_pk)
            ).group_by(DecisionV2.category_1).all()
            
            stats['by_category'] = {cat: count for cat, count in category_stats if cat}
            
            return stats
            
        finally:
            session.close()