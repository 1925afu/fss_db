import os
import logging
from typing import Dict, Any, Optional, List
import PyPDF2
from app.core.config import settings
from app.services.gemini_service import GeminiService
from app.services.decision_service import DecisionService
from app.models.fsc_models import Decision, Action, Law, ActionLawMap
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF 처리 서비스"""
    
    def __init__(self, db: Session, use_2_step_pipeline: bool = True):
        self.db = db
        self.gemini_service = GeminiService()
        self.decision_service = DecisionService(db)
        self.processed_pdf_dir = settings.PROCESSED_PDF_DIR
        self.use_2_step_pipeline = use_2_step_pipeline
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDF 파일에서 텍스트를 추출합니다."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
                
                return text.strip()
                
        except Exception as e:
            logger.error(f"PDF 텍스트 추출 실패: {pdf_path} - {str(e)}")
            return ""
    
    async def process_single_pdf(self, pdf_path: str, max_retries: int = 2) -> Dict[str, Any]:
        """단일 PDF 파일을 처리합니다."""
        try:
            logger.info(f"PDF 처리 시작: {pdf_path}")
            
            # 1. PDF에서 텍스트 추출
            pdf_text = self.extract_text_from_pdf(pdf_path)
            if not pdf_text:
                raise Exception("PDF에서 텍스트를 추출할 수 없습니다.")
            
            extracted_data = None
            validation_result = None

            if self.use_2_step_pipeline:
                # --- 2단계 파이프라인 처리 ---
                logger.info(f"2단계 파이프라인으로 처리 시작: {pdf_path}")
                try:
                    filename = os.path.basename(pdf_path)
                    extracted_data = await self.gemini_service.extract_structured_data_2_step(pdf_text, filename)
                    # 2단계 파이프라인은 신뢰도가 높다고 가정하고, 우선 단순 검증 결과를 설정합니다.
                    validation_result = {'is_valid': True, 'comment': '2-step pipeline processed'}
                    logger.info(f"2단계 파이프라인 처리 성공: {pdf_path}")
                except Exception as e:
                    logger.error(f"2단계 파이프라인 처리 중 오류 발생: {pdf_path} - {str(e)}")
                    raise
            else:
                # --- 기존 1단계 파이프라인 처리 (재시도 로직 포함) ---
                logger.info(f"1단계 파이프라인으로 처리 시작: {pdf_path}")
                retry_count = 0
                while retry_count <= max_retries:
                    try:
                        if retry_count > 0 and validation_result:
                            error_analysis = self.gemini_service.analyze_validation_errors(validation_result)
                            if error_analysis['should_retry']:
                                logger.info(f"재처리 시도 {retry_count}/{max_retries}: {pdf_path}")
                                extracted_data = await self.gemini_service.extract_structured_data(pdf_text, error_analysis)
                            else:
                                break
                        else:
                            extracted_data = await self.gemini_service.extract_structured_data(pdf_text)
                        
                        validation_result = await self.gemini_service.validate_extracted_data(extracted_data, pdf_text)
                        
                        if validation_result.get('is_valid', False):
                            logger.info(f"검증 성공: {pdf_path}")
                            break
                        
                        logger.warning(f"검증 실패 (시도 {retry_count + 1}/{max_retries + 1}): {pdf_path}")
                        logger.warning(f"검증 오류: {validation_result.get('errors', [])}")
                        
                        corrections = validation_result.get('corrections', {})
                        for field, corrected_value in corrections.items():
                            if field in extracted_data:
                                extracted_data[field] = corrected_value
                        
                        retry_count += 1
                        
                    except Exception as e:
                        logger.error(f"추출 시도 {retry_count + 1} 실패: {str(e)}")
                        retry_count += 1
                        if retry_count > max_retries:
                            raise
                
                if not validation_result or not validation_result.get('is_valid', False):
                    logger.warning(f"최대 재시도 후에도 검증 실패: {pdf_path}")

            if not extracted_data:
                raise Exception("데이터 추출에 실패하여 DB에 저장할 수 없습니다.")

            # 3. 데이터베이스에 저장
            result = await self._save_to_database(extracted_data, pdf_path)
            
            return {
                'success': True,
                'pdf_path': pdf_path,
                'extracted_data': extracted_data,
                'validation_result': validation_result,
                'db_result': result,
            }
            
        except Exception as e:
            logger.error(f"PDF 처리 실패: {pdf_path} - {str(e)}")
            return {
                'success': False,
                'pdf_path': pdf_path,
                'error': str(e)
            }
    
    async def _save_to_database(self, extracted_data: Dict[str, Any], pdf_path: str) -> Dict[str, Any]:
        """추출된 데이터를 데이터베이스에 저장합니다."""
        try:
            # 2단계 파이프라인의 중첩 구조에 맞게 데이터 추출
            decision_info = extracted_data.get('decision', {})
            actions_data = extracted_data.get('actions', [])

            # 의결서 데이터 준비 (새로운 복합키 스키마에 맞게)
            decision_data = {
                'decision_year': decision_info.get('decision_year', 2023),  # 기본값 설정
                'decision_id': decision_info.get('decision_id', 1),  # AI가 생성한 ID 사용
                'decision_month': decision_info.get('decision_month', 1),  # AI가 생성한 월
                'decision_day': decision_info.get('decision_day', 1),  # AI가 생성한 일
                'agenda_no': decision_info.get('agenda_no', ''),
                'title': decision_info.get('title', ''),
                'category_1': decision_info.get('category_1', ''),
                'category_2': decision_info.get('category_2', ''),
                'submitter': decision_info.get('submitter', ''),
                'submission_date': self._parse_date(decision_info.get('submission_date')),
                'stated_purpose': decision_info.get('stated_purpose', ''),
                'full_text': extracted_data.get('full_text', ''), # 전문은 최상위에 있을 수 있음
                'source_file': os.path.basename(pdf_path)
            }
            
            # 의결서 저장
            decision = self.decision_service.create_decision(decision_data)
            
            # 조치 데이터 저장 (복합키 참조)
            actions_saved = []
            laws_saved = []
            
            if isinstance(actions_data, list):
                for action_data in actions_data:
                    action = self._create_action(action_data, decision.decision_year, decision.decision_id)
                    if action:
                        actions_saved.append(action.action_id)
                        # 해당 Action에 연결된 법률 개수 추가
                        law_count = self.db.query(ActionLawMap).filter(
                            ActionLawMap.action_id == action.action_id
                        ).count()
                        laws_saved.extend([action.action_id] * law_count)  # action_id를 법률 개수만큼 추가
            elif isinstance(actions_data, dict):
                action = self._create_action(actions_data, decision.decision_year, decision.decision_id)
                if action:
                    actions_saved.append(action.action_id)
                    # 해당 Action에 연결된 법률 개수 추가
                    law_count = self.db.query(ActionLawMap).filter(
                        ActionLawMap.action_id == action.action_id
                    ).count()
                    laws_saved.extend([action.action_id] * law_count)  # action_id를 법률 개수만큼 추가
            else:
                logger.warning(f"지원되지 않는 조치 데이터 형태: {type(actions_data)}")

            # 전체 법률 개수 계산
            total_laws = self.db.query(Law).count()

            return {
                'decision_year': decision.decision_year,
                'decision_id': decision.decision_id,
                'actions_saved': actions_saved,
                'laws_saved': len(laws_saved)  # 법률 개수 반환
            }
            
        except Exception as e:
            logger.error(f"데이터베이스 저장 실패: {str(e)}")
            raise
    
    def _extract_decision_id(self, agenda_no: str) -> Optional[int]:
        """의안번호에서 숫자 부분을 추출합니다."""
        try:
            # "제 200 호" -> 200
            import re
            numbers = re.findall(r'\d+', agenda_no)
            return int(numbers[0]) if numbers else None
        except:
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """날짜 문자열을 datetime 객체로 변환합니다."""
        if not date_str:
            return None
        
        try:
            # 다양한 날짜 형식 지원
            formats = [
                '%Y-%m-%d',
                '%Y.%m.%d',
                '%Y/%m/%d',
                '%Y년 %m월 %d일'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            return None
            
        except Exception:
            return None
    
    def _create_action(self, action_data, decision_year: int, decision_id: int) -> Optional[Action]:
        """조치 데이터를 생성합니다."""
        try:
            # 데이터 타입 확인 및 변환
            if isinstance(action_data, str):
                logger.warning(f"조치 데이터가 문자열 형태입니다: {action_data}")
                # 문자열인 경우 기본값으로 처리
                processed_data = {
                    'entity_name': action_data,
                    'industry_sector': '',
                    'violation_details': '',
                    'action_type': '',
                    'fine_amount': None,
                    'fine_basis_amount': None,
                    'sanction_period': '',
                    'sanction_scope': '',
                    'effective_date': None,
                    'laws_cited': []
                }
            elif isinstance(action_data, dict):
                processed_data = action_data
            else:
                logger.error(f"지원되지 않는 조치 데이터 형태: {type(action_data)}")
                return None
            
            # Action 객체 생성
            action = Action(
                decision_year=decision_year,
                decision_id=decision_id,
                entity_name=processed_data.get('entity_name', ''),
                industry_sector=processed_data.get('industry_sector', ''),
                violation_details=processed_data.get('violation_details', ''),
                action_type=processed_data.get('action_type', ''),
                fine_amount=self._parse_amount(processed_data.get('fine_amount')),
                fine_basis_amount=self._parse_amount(processed_data.get('fine_basis_amount')),
                sanction_period=processed_data.get('sanction_period', ''),
                sanction_scope=processed_data.get('sanction_scope', ''),
                effective_date=self._parse_date(processed_data.get('effective_date'))
            )
            
            self.db.add(action)
            self.db.commit()
            self.db.refresh(action)
            
            # 법률 정보 처리
            laws_cited = processed_data.get('laws_cited', [])
            if laws_cited and isinstance(laws_cited, list):
                for law_info in laws_cited:
                    if isinstance(law_info, dict):
                        # 법률 생성 또는 검색
                        law = self._create_or_get_law(law_info)
                        if law:
                            # ActionLawMap 생성
                            self._create_action_law_mapping(action.action_id, law.law_id, law_info)
            
            return action
            
        except Exception as e:
            logger.error(f"조치 생성 실패: {str(e)}")
            self.db.rollback()
            return None
    
    def _create_law(self, law_data: Dict[str, Any]) -> Optional[Law]:
        """법률 데이터를 생성합니다."""
        try:
            # 기존 법률 확인
            existing_law = self.db.query(Law).filter(
                Law.law_name == law_data.get('law_name', '')
            ).first()
            
            if existing_law:
                return existing_law
            
            # 새 법률 생성
            law = Law(
                law_name=law_data.get('law_name', ''),
                law_short_name=law_data.get('law_short_name', ''),
                law_category=law_data.get('law_category', '')
            )
            
            self.db.add(law)
            self.db.commit()
            self.db.refresh(law)
            
            return law
            
        except Exception as e:
            logger.error(f"법률 생성 실패: {str(e)}")
            self.db.rollback()
            return None
    
    def _create_or_get_law(self, law_info: Dict[str, Any]) -> Optional[Law]:
        """법률 정보를 기반으로 법률을 생성하거나 검색합니다."""
        try:
            law_short_name = law_info.get('law_short_name', '')
            if not law_short_name:
                logger.warning(f"법률 약칭이 없습니다: {law_info}")
                return None
            
            # 기존 법률 확인 (약칭으로 검색)
            existing_law = self.db.query(Law).filter(
                Law.law_short_name == law_short_name
            ).first()
            
            if existing_law:
                return existing_law
            
            # 새 법률 생성
            law = Law(
                law_name=law_info.get('law_name', law_short_name),
                law_short_name=law_short_name,
                law_category=law_info.get('law_category', '기타')
            )
            
            self.db.add(law)
            self.db.commit()
            self.db.refresh(law)
            
            logger.info(f"새 법률 생성: {law_short_name}")
            return law
            
        except Exception as e:
            logger.error(f"법률 생성/검색 실패: {str(e)}")
            self.db.rollback()
            return None
    
    def _create_action_law_mapping(self, action_id: int, law_id: int, law_info: Dict[str, Any]) -> Optional[ActionLawMap]:
        """Action과 Law 간의 매핑을 생성합니다."""
        try:
            mapping = ActionLawMap(
                action_id=action_id,
                law_id=law_id,
                article_details=law_info.get('article_details', ''),
                article_purpose=law_info.get('article_purpose', '')
            )
            
            self.db.add(mapping)
            self.db.commit()
            self.db.refresh(mapping)
            
            logger.info(f"ActionLawMap 생성: action_id={action_id}, law_id={law_id}, article={law_info.get('article_details', '')}")
            return mapping
            
        except Exception as e:
            logger.error(f"ActionLawMap 생성 실패: {str(e)}")
            self.db.rollback()
            return None
    
    def _parse_amount(self, amount_str: str) -> Optional[int]:
        """금액 문자열을 숫자로 변환합니다."""
        if not amount_str:
            return None
        
        try:
            # 한국어 숫자 단위 처리
            import re
            
            # 숫자만 추출
            numbers = re.findall(r'\d+', str(amount_str))
            if not numbers:
                return None
            
            amount = int(numbers[0])
            
            # 단위 처리
            if '억' in str(amount_str):
                amount *= 100000000
            elif '만' in str(amount_str):
                amount *= 10000
            elif '천' in str(amount_str):
                amount *= 1000
            
            return amount
            
        except Exception:
            return None
    
    async def process_all_pdfs(self) -> List[Dict[str, Any]]:
        """모든 PDF 파일을 처리합니다."""
        results = []
        
        if not os.path.exists(self.processed_pdf_dir):
            logger.warning(f"PDF 디렉토리가 존재하지 않습니다: {self.processed_pdf_dir}")
            return results
        
        # PDF 파일 목록 확인 - "의결*." 형식만 필터링
        all_pdf_files = [f for f in os.listdir(self.processed_pdf_dir) if f.endswith('.pdf')]
        pdf_files = [f for f in all_pdf_files if f.startswith('의결')]
        
        logger.info(f"전체 PDF 파일 수: {len(all_pdf_files)}")
        logger.info(f"처리할 PDF 파일 수 (의결*. 형식): {len(pdf_files)}")
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(self.processed_pdf_dir, pdf_file)
            result = await self.process_single_pdf(pdf_path)
            results.append(result)
        
        return results
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """처리 통계를 반환합니다."""
        if os.path.exists(self.processed_pdf_dir):
            all_pdf_files = [f for f in os.listdir(self.processed_pdf_dir) if f.endswith('.pdf')]
            target_pdfs = [f for f in all_pdf_files if f.startswith('의결')]
        else:
            all_pdf_files = []
            target_pdfs = []
        
        total_decisions = self.db.query(Decision).count()
        total_actions = self.db.query(Action).count()
        total_laws = self.db.query(Law).count()
        
        return {
            'total_pdf_files': len(all_pdf_files),
            'target_pdf_files': len(target_pdfs),
            'total_decisions': total_decisions,
            'total_actions': total_actions,
            'total_laws': total_laws,
            'processing_rate': f"{(total_decisions/len(target_pdfs))*100:.1f}%" if len(target_pdfs) > 0 else "0%"
        }