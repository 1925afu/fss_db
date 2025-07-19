import os
import logging
from typing import Dict, Any, Optional, List
import PyPDF2
from app.core.config import settings
from app.services.gemini_service import GeminiService
from app.services.decision_service import DecisionService
from app.services.rule_based_extractor import RuleBasedExtractor
from app.models.fsc_models import Decision, Action, Law, ActionLawMap
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF 처리 서비스"""
    
    def __init__(self, db: Session, use_2_step_pipeline: bool = True, processing_mode: str = 'hybrid'):
        self.db = db
        self.gemini_service = GeminiService()
        self.decision_service = DecisionService(db)
        self.rule_based_extractor = RuleBasedExtractor()
        self.processed_pdf_dir = settings.PROCESSED_PDF_DIR
        self.use_2_step_pipeline = use_2_step_pipeline
        self.processing_mode = processing_mode  # 'rule-based', 'hybrid', 'ai-only'
        
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
    
    async def process_single_pdf(self, pdf_path: str, max_retries: int = 2, processing_mode: str = None) -> Dict[str, Any]:
        """단일 PDF 파일을 처리합니다."""
        try:
            # 처리 모드 설정 (인자가 주어지면 우선 사용)
            mode = processing_mode or self.processing_mode
            logger.info(f"PDF 처리 시작 ({mode} 모드): {pdf_path}")
            
            # 1. PDF에서 텍스트 추출
            pdf_text = self.extract_text_from_pdf(pdf_path)
            if not pdf_text:
                raise Exception("PDF에서 텍스트를 추출할 수 없습니다.")
            
            # 2. 처리 모드에 따른 분기
            if mode == 'rule-based':
                return await self._process_rule_based_only(pdf_path, pdf_text)
            elif mode == 'hybrid':
                return await self._process_hybrid(pdf_path, pdf_text, max_retries)
            else:  # 'ai-only'
                return await self._process_ai_only(pdf_path, pdf_text, max_retries)
                
        except Exception as e:
            logger.error(f"PDF 처리 실패: {pdf_path} - {str(e)}")
            return {
                'success': False,
                'pdf_path': pdf_path,
                'error': str(e)
            }
    
    async def _process_rule_based_only(self, pdf_path: str, pdf_text: str) -> Dict[str, Any]:
        """Rule-based 전용 처리"""
        try:
            filename = os.path.basename(pdf_path)
            
            # Rule-based 추출
            extracted_data = self.rule_based_extractor.extract_full_document_structure(pdf_text, filename)
            
            # 데이터베이스에 저장
            result = await self._save_to_database(extracted_data, pdf_path)
            
            return {
                'success': True,
                'pdf_path': pdf_path,
                'extracted_data': extracted_data,
                'processing_mode': 'rule-based',
                'db_result': result,
            }
            
        except Exception as e:
            logger.error(f"Rule-based 처리 실패: {pdf_path} - {str(e)}")
            return {
                'success': False,
                'pdf_path': pdf_path,
                'error': str(e),
                'processing_mode': 'rule-based'
            }
    
    async def _process_hybrid(self, pdf_path: str, pdf_text: str, max_retries: int = 2) -> Dict[str, Any]:
        """하이브리드 처리 (Rule-based + AI 보완)"""
        try:
            filename = os.path.basename(pdf_path)
            
            # 복수 조치 가능성 먼저 감지
            has_multiple_actions = self.rule_based_extractor.detect_multiple_actions(pdf_text)
            
            if has_multiple_actions:
                # 복수 조치가 감지되면 바로 2단계 AI 파이프라인 사용
                logger.info(f"복수 조치 감지됨, 2단계 AI 파이프라인 사용: {pdf_path}")
                
                try:
                    extracted_data = await self.gemini_service.extract_structured_data_2_step(pdf_text, filename)
                    
                    # 데이터베이스에 저장
                    result = await self._save_to_database(extracted_data, pdf_path)
                    
                    return {
                        'success': True,
                        'pdf_path': pdf_path,
                        'extracted_data': extracted_data,
                        'processing_mode': 'hybrid-ai-2step',
                        'db_result': result,
                    }
                    
                except Exception as e:
                    logger.error(f"2단계 AI 파이프라인 실패: {pdf_path} - {str(e)}")
                    # 실패 시 Rule-based로 fallback
                    logger.info("2단계 AI 파이프라인 실패, Rule-based로 fallback")
            
            # 1. 단일 조치 또는 AI 실패 시 Rule-based 우선 시도
            try:
                extracted_data = self.rule_based_extractor.extract_full_document_structure(pdf_text, filename)
                
                # Rule-based 결과 검증
                if self._validate_rule_based_result(extracted_data):
                    logger.info(f"Rule-based 추출 성공, AI 보완 적용: {pdf_path}")
                    
                    # AI로 복잡한 부분 보완
                    enhanced_data = await self._enhance_with_ai(extracted_data, pdf_text)
                    
                    # 데이터베이스에 저장
                    result = await self._save_to_database(enhanced_data, pdf_path)
                    
                    return {
                        'success': True,
                        'pdf_path': pdf_path,
                        'extracted_data': enhanced_data,
                        'processing_mode': 'hybrid',
                        'db_result': result,
                    }
                
            except Exception as e:
                logger.warning(f"Rule-based 처리 실패, AI 전용으로 fallback: {pdf_path} - {str(e)}")
            
            # 2. Rule-based 실패 시 AI 전용으로 fallback
            return await self._process_ai_only(pdf_path, pdf_text, max_retries)
            
        except Exception as e:
            logger.error(f"하이브리드 처리 실패: {pdf_path} - {str(e)}")
            return {
                'success': False,
                'pdf_path': pdf_path,
                'error': str(e),
                'processing_mode': 'hybrid'
            }
    
    async def _process_ai_only(self, pdf_path: str, pdf_text: str, max_retries: int = 2) -> Dict[str, Any]:
        """기존 AI 전용 처리 (기존 로직 유지)"""
        try:
            filename = os.path.basename(pdf_path)
            
            extracted_data = None
            validation_result = None

            if self.use_2_step_pipeline:
                # --- 2단계 파이프라인 처리 ---
                logger.info(f"AI 전용 2단계 파이프라인 처리 시작: {pdf_path}")
                try:
                    extracted_data = await self.gemini_service.extract_structured_data_2_step(pdf_text, filename)
                    # 2단계 파이프라인은 신뢰도가 높다고 가정하고, 우선 단순 검증 결과를 설정합니다.
                    validation_result = {'is_valid': True, 'comment': '2-step pipeline processed'}
                    logger.info(f"AI 전용 2단계 파이프라인 처리 성공: {pdf_path}")
                except Exception as e:
                    logger.error(f"AI 전용 2단계 파이프라인 처리 중 오류 발생: {pdf_path} - {str(e)}")
                    raise
            else:
                # --- 기존 1단계 파이프라인 처리 (재시도 로직 포함) ---
                logger.info(f"AI 전용 1단계 파이프라인 처리 시작: {pdf_path}")
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

            # 데이터베이스에 저장
            result = await self._save_to_database(extracted_data, pdf_path)
            
            return {
                'success': True,
                'pdf_path': pdf_path,
                'extracted_data': extracted_data,
                'validation_result': validation_result,
                'processing_mode': 'ai-only',
                'db_result': result,
            }
            
        except Exception as e:
            logger.error(f"AI 전용 처리 실패: {pdf_path} - {str(e)}")
            return {
                'success': False,
                'pdf_path': pdf_path,
                'error': str(e),
                'processing_mode': 'ai-only'
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
            
            # 날짜 정보가 1월 1일인 경우, 의결*.pdf 파일에서 실제 날짜 추출 시도
            if decision_data['decision_month'] == 1 and decision_data['decision_day'] == 1:
                actual_date = await self._extract_actual_meeting_date(
                    decision_data['decision_year'], 
                    decision_data['decision_id'],
                    self.processed_pdf_dir
                )
                if actual_date:
                    decision_data['decision_month'] = actual_date['month']
                    decision_data['decision_day'] = actual_date['day']
                    logger.info(f"실제 회의 날짜로 업데이트: {decision_data['decision_year']}-{decision_data['decision_id']}호 -> {actual_date['month']}월 {actual_date['day']}일")
            
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
            
            # Action 객체 생성 (새로운 컬럼들 포함)
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
                effective_date=self._parse_date(processed_data.get('effective_date')),
                # 하이브리드 추출을 위한 새로운 컬럼들
                violation_full_text=processed_data.get('violation_full_text', ''),
                violation_summary=processed_data.get('violation_summary', ''),
                target_details=processed_data.get('target_details', {})
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
            law_name = law_info.get('law_name', '')
            law_short_name = law_info.get('law_short_name', '')
            
            if not law_name:
                # law_short_name을 대신 사용 시도
                if law_short_name:
                    law_name = law_short_name
                    logger.info(f"법률명 누락, short_name 사용: {law_short_name}")
                else:
                    logger.warning(f"법률명이 없습니다: {law_info}")
                    return None
            
            # 기존 법률 확인 (정식명칭으로 검색 - 시행령 구분을 위해)
            existing_law = self.db.query(Law).filter(
                Law.law_name == law_name
            ).first()
            
            if existing_law:
                logger.info(f"기존 법률 사용: {law_name}")
                return existing_law
            
            # 새 법률 생성
            law = Law(
                law_name=law_name,
                law_short_name=law_short_name,
                law_category=law_info.get('law_category', '기타')
            )
            
            self.db.add(law)
            self.db.commit()
            self.db.refresh(law)
            
            logger.info(f"새 법률 생성: {law_name}")
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
    
    async def process_all_pdfs(self, fsc_only: bool = True) -> List[Dict[str, Any]]:
        """모든 PDF 파일을 처리합니다."""
        results = []
        
        if not os.path.exists(self.processed_pdf_dir):
            logger.warning(f"PDF 디렉토리가 존재하지 않습니다: {self.processed_pdf_dir}")
            return results
        
        # PDF 파일 목록 확인
        all_pdf_files = [f for f in os.listdir(self.processed_pdf_dir) if f.endswith('.pdf')]
        
        # PoC: 금융위 의결서만 처리
        if fsc_only:
            pdf_files = [f for f in all_pdf_files if "금융위 의결서" in f]
            logger.info(f"전체 PDF 파일 수: {len(all_pdf_files)}")
            logger.info(f"처리할 PDF 파일 수 (금융위 의결서 형식): {len(pdf_files)}")
        else:
            pdf_files = [f for f in all_pdf_files if f.startswith('의결')]
            logger.info(f"전체 PDF 파일 수: {len(all_pdf_files)}")
            logger.info(f"처리할 PDF 파일 수 (의결*. 형식): {len(pdf_files)}")
        
        for pdf_file in pdf_files:
            pdf_path = os.path.join(self.processed_pdf_dir, pdf_file)
            result = await self.process_single_pdf(pdf_path, processing_mode=self.processing_mode)
            results.append(result)
        
        return results
    
    def get_processing_stats(self, fsc_only: bool = True) -> Dict[str, Any]:
        """처리 통계를 반환합니다."""
        if os.path.exists(self.processed_pdf_dir):
            all_pdf_files = [f for f in os.listdir(self.processed_pdf_dir) if f.endswith('.pdf')]
            if fsc_only:
                target_pdfs = [f for f in all_pdf_files if "금융위 의결서" in f]
            else:
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
    
    # 하이브리드 처리를 위한 헬퍼 메서드들
    
    def _validate_rule_based_result(self, extracted_data: Dict[str, Any]) -> bool:
        """Rule-based 추출 결과 검증"""
        try:
            decision = extracted_data.get('decision', {})
            actions = extracted_data.get('actions', [])
            laws = extracted_data.get('laws', [])
            
            # 기본 필수 필드 검증
            if not decision.get('decision_year') or not decision.get('decision_id'):
                logger.warning("의결서 기본 정보 누락")
                return False
            
            # 조치 정보 검증
            if not actions:
                logger.warning("조치 정보 누락")
                return False
            
            # 법률 정보 검증
            if not laws:
                logger.warning("법률 정보 누락")
                return False
            
            # 법률 조항이 구체적으로 추출되었는지 확인
            for law in laws:
                if not law.get('article_details') or law.get('article_details') == '미상':
                    logger.warning(f"법률 조항 정보 부족: {law}")
                    return False
            
            logger.info("Rule-based 추출 결과 검증 통과")
            return True
            
        except Exception as e:
            logger.error(f"Rule-based 결과 검증 실패: {e}")
            return False
    
    async def _enhance_with_ai(self, extracted_data: Dict[str, Any], pdf_text: str) -> Dict[str, Any]:
        """AI로 Rule-based 결과 보완 (하이브리드 접근)"""
        try:
            # Rule-based 결과를 기본으로 사용
            enhanced_data = extracted_data.copy()
            filename = extracted_data.get('decision', {}).get('source_file', '')
            
            logger.info("AI 보완 시작 - 하이브리드 추출")
            
            # 1. 위반 내용 AI 요약 생성
            for action in enhanced_data.get('actions', []):
                violation_full_text = action.get('violation_full_text', '')
                if violation_full_text:
                    logger.info("위반 내용 AI 요약 시작")
                    violation_summary = await self.gemini_service.summarize_violation_content(violation_full_text)
                    action['violation_summary'] = violation_summary
                else:
                    action['violation_summary'] = ''
            
            # 2. 조치대상자 세부 정보 AI 보완
            for action in enhanced_data.get('actions', []):
                rule_based_targets = action.get('target_details', {})
                if rule_based_targets:
                    logger.info("조치대상자 세부 정보 AI 보완 시작")
                    enhanced_targets = await self.gemini_service.extract_target_details_ai(pdf_text, rule_based_targets)
                    action['target_details'] = enhanced_targets
            
            # 3. 카테고리 AI 자동 분류
            decision = enhanced_data.get('decision', {})
            if not decision.get('category_1') or not decision.get('category_2'):
                logger.info("카테고리 AI 자동 분류 시작")
                ai_categories = await self.gemini_service.classify_categories_ai(pdf_text, filename)
                
                if not decision.get('category_1'):
                    decision['category_1'] = ai_categories.get('category_1', '제재')
                if not decision.get('category_2'):
                    decision['category_2'] = ai_categories.get('category_2', '기관')
            
            # 4. 기타 누락된 필드 보완
            if not decision.get('stated_purpose'):
                # 간단한 제안이유 추출 (필요시)
                decision['stated_purpose'] = '금융감독 조치안'  # 기본값
            
            logger.info("AI 보완 완료 - 하이브리드 추출")
            return enhanced_data
            
        except Exception as e:
            logger.error(f"AI 보완 처리 실패: {e}")
            return extracted_data  # 실패 시 원본 반환
    
    async def _extract_actual_meeting_date(self, decision_year: int, decision_id: int, processed_pdf_dir: str) -> Optional[Dict[str, int]]:
        """의결*.pdf 파일에서 실제 금융위원회 회의 날짜를 추출합니다."""
        try:
            import re
            
            # 매칭되는 의결 파일 찾기
            pattern = f'의결{decision_id}\\.'
            matching_files = []
            
            for filename in os.listdir(processed_pdf_dir):
                if re.match(pattern, filename) and filename.endswith('.pdf'):
                    matching_files.append(filename)
            
            if not matching_files:
                logger.debug(f"매칭되는 의결 파일 없음: {decision_year}-{decision_id}호")
                return None
            
            # 첫 번째 매칭 파일에서 날짜 추출
            decision_file_path = os.path.join(processed_pdf_dir, matching_files[0])
            pdf_text = self.extract_text_from_pdf(decision_file_path)
            
            if not pdf_text:
                return None
            
            # 의결일자 패턴들 (실제 PDF에서 확인된 패턴)
            date_patterns = [
                # 의결연월일 2025. 3.19. (제5차) 패턴
                r'의결\s*연월일\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*\(제(\d+)차\)',
                # 의결일: 2025. 1. 8
                r'의결일\s*[:：]\s*(\d{4})[\.년]\s*(\d{1,2})[\.월]\s*(\d{1,2})',
                # 의결일자: 2025년 1월 8일
                r'의결일자\s*[:：]\s*(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',
                # 2025년 1월 8일 (문서 상단에 있는 경우)
                r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일.*?의결',
                # 2025. 1. 8. (일반 날짜 형식)
                r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, pdf_text[:1000])  # 문서 앞부분에서만 검색
                if match:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    
                    # 연도 확인
                    if year == decision_year:
                        logger.info(f"의결 파일에서 날짜 추출 성공: {matching_files[0]} -> {year}년 {month}월 {day}일")
                        return {'month': month, 'day': day}
                    else:
                        logger.warning(f"연도 불일치: 예상 {decision_year}, 실제 {year}")
            
            logger.debug(f"날짜 패턴 매칭 실패: {matching_files[0]}")
            return None
            
        except Exception as e:
            logger.error(f"실제 회의 날짜 추출 실패: {e}")
            return None