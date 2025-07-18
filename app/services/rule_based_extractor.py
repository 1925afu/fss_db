import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class RuleBasedExtractor:
    """Rule-based 추출기 - 금융위 의결서 표준 포맷 대응"""
    
    def __init__(self):
        # 정규식 패턴 정의
        self.patterns = {
            # 의결 정보 패턴
            'decision_number': r'제(\d{4})-(\d+)호',
            'decision_date': r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',
            
            # 근거법규 섹션 패턴 (더 유연하게)
            'law_section': r'나\.\s*근거법규(.*?)(?=다\.|라\.|마\.|바\.|사\.|아\.|자\.|차\.|카\.|타\.|파\.|하\.|$)',
            
            # 법률명과 조항 패턴
            'law_with_articles': r'[｢「]([^｣」]+)[｣」]\s*([^｢「\n]+?)(?=[｢「]|$|\n\s*\n)',
            'article_pattern': r'제(\d+)조(?:\s*제(\d+)항)?(?:\s*제(\d+)호)?(?:의\s*(\d+))?',
            
            # 금액 패턴
            'amount_million': r'(\d+(?:,\d{3})*)\s*백만원',
            'amount_won': r'(\d+(?:,\d{3})*)\s*원',
            
            # 기관명 패턴
            'entity_name': r'([^에\s]+)(?:에\s*대한|의\s*)',
            
            # 업권 분류 키워드
            'industry_keywords': {
                '은행': ['은행', '저축은행'],
                '보험': ['보험', '생명보험', '손해보험'],
                '금융투자': ['자산운용', '투자', '증권', '선물'],
                '회계/감사': ['회계법인', '감사', '회계사']
            },
            
            # 조치 이유 섹션 패턴
            'violation_section': r'가\.\s*지적사항(.*?)(?=나\.|라\.|마\.|바\.|사\.|아\.|자\.|차\.|카\.|타\.|파\.|하\.|$)',
            
            # 조치대상자 정보 패턴
            'target_info_section': r'1\.\s*조치대상자의\s*인적사항(.*?)(?=2\.|$)',
            'target_types': {
                '기관': r'기\s*관\s*([^\n]+)',
                '임직원': r'임직원\s*([^\n]+)',
                '외부감사인': r'외부감사인\s*([^\n]+)'
            }
        }
    
    def extract_decision_metadata(self, text: str, filename: str) -> Dict[str, Any]:
        """의결서 메타데이터 추출"""
        try:
            metadata = {}
            
            # 파일명에서 의결번호 추출
            filename_match = re.search(self.patterns['decision_number'], filename)
            if filename_match:
                metadata['decision_year'] = int(filename_match.group(1))
                metadata['decision_id'] = int(filename_match.group(2))
            
            # 텍스트에서 의결일자 추출
            date_match = re.search(self.patterns['decision_date'], text)
            if date_match:
                year = int(date_match.group(1))
                month = int(date_match.group(2))
                day = int(date_match.group(3))
                
                metadata['decision_year'] = year
                metadata['decision_month'] = month
                metadata['decision_day'] = day
            
            # 제목 추출 (파일명에서)
            title_match = re.search(r'_([^_]+?)(?:\(공개용\))?\.pdf$', filename)
            if title_match:
                metadata['title'] = title_match.group(1)
            
            # 기본값 설정
            metadata.setdefault('decision_year', 2024)
            metadata.setdefault('decision_id', 1)
            metadata.setdefault('decision_month', 1)
            metadata.setdefault('decision_day', 1)
            metadata.setdefault('title', '')
            
            # 의안번호 생성
            metadata['agenda_no'] = f"제{metadata['decision_id']}호"
            
            logger.info(f"메타데이터 추출 완료: {metadata}")
            return metadata
            
        except Exception as e:
            logger.error(f"메타데이터 추출 실패: {e}")
            return {
                'decision_year': 2024,
                'decision_id': 1,
                'decision_month': 1,
                'decision_day': 1,
                'agenda_no': '제1호',
                'title': ''
            }
    
    def extract_laws_and_articles(self, text: str) -> List[Dict[str, Any]]:
        """근거법규 섹션에서 법률과 조항 추출"""
        try:
            laws = []
            
            # 근거법규 섹션 찾기
            law_section_match = re.search(self.patterns['law_section'], text, re.DOTALL | re.IGNORECASE)
            
            if not law_section_match:
                logger.warning("근거법규 섹션을 찾을 수 없습니다.")
                return laws
            
            law_section_text = law_section_match.group(1)
            logger.info(f"근거법규 섹션 발견: {law_section_text[:100]}...")
            
            # 법률명과 조항을 함께 추출 (개선된 방식)
            # 각 줄을 개별적으로 처리하여 모든 법률을 잡아냄
            lines = law_section_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line or not '｢' in line:
                    continue
                    
                # 법률명 추출
                law_name_match = re.search(r'[｢「]([^｣」]+)[｣」]', line)
                if not law_name_match:
                    continue
                    
                law_name = law_name_match.group(1).strip()
                
                # 해당 줄에서 조항 추출
                article_matches = re.findall(self.patterns['article_pattern'], line)
                
                if article_matches:
                    for article_match in article_matches:
                        article_num = article_match[0]
                        paragraph = article_match[1] if article_match[1] else ''
                        item = article_match[2] if article_match[2] else ''
                        sub_item = article_match[3] if article_match[3] else ''
                        
                        # 조항 세부 사항 조합
                        article_details = f"제{article_num}조"
                        if paragraph:
                            article_details += f" 제{paragraph}항"
                        if item:
                            article_details += f" 제{item}호"
                        if sub_item:
                            article_details += f"의 {sub_item}"
                        
                        # 법률 약칭 생성
                        law_short_name = law_name.replace(' 시행령', '').replace(' 시행규칙', '').strip()
                        
                        # 법률 카테고리 결정
                        law_category = self._determine_law_category(law_name)
                        
                        laws.append({
                            'law_name': law_name,
                            'law_short_name': law_short_name,
                            'law_category': law_category,
                            'article_details': article_details,
                            'article_purpose': ''  # Rule-based로는 내용 요약 어려움
                        })
                else:
                    # 조항이 없는 경우 법률명만 기록
                    law_short_name = law_name.replace(' 시행령', '').replace(' 시행규칙', '').strip()
                    law_category = self._determine_law_category(law_name)
                    
                    laws.append({
                        'law_name': law_name,
                        'law_short_name': law_short_name,
                        'law_category': law_category,
                        'article_details': '',
                        'article_purpose': ''
                    })
            
            logger.info(f"추출된 법률 수: {len(laws)}")
            for law in laws:
                logger.info(f"법률: {law['law_name']} - {law['article_details']}")
            
            return laws
            
        except Exception as e:
            logger.error(f"법률 조항 추출 실패: {e}")
            return []
    
    def _determine_law_category(self, law_name: str) -> str:
        """법률명을 기반으로 카테고리 결정"""
        if '은행' in law_name:
            return '은행법'
        elif '보험' in law_name:
            return '보험법'
        elif '자본시장' in law_name or '금융투자' in law_name:
            return '자본시장법'
        elif '지배구조' in law_name:
            return '지배구조법'
        else:
            return '기타'
    
    def extract_actions_and_violations(self, text: str, filename: str = '') -> List[Dict[str, Any]]:
        """조치와 위반 내용 추출"""
        try:
            actions = []
            
            # 기관명 추출 (파일명에서 우선 추출)
            entity_name = ''
            
            # 1. 파일명에서 기관명 추출 시도
            filename_entity_match = re.search(r'_([^_]+?)에 대한', filename)
            if filename_entity_match:
                entity_name = filename_entity_match.group(1)
            else:
                # 2. 텍스트에서 기관명 추출 시도
                entity_match = re.search(self.patterns['entity_name'], text)
                entity_name = entity_match.group(1) if entity_match else '조치대상자'
            
            # 업권 분류
            industry_sector = self._classify_industry(text, entity_name)
            
            # 금액 추출
            fine_amount = self._extract_fine_amount(text)
            
            # 조치 유형 추출
            action_type = self._extract_action_type(text, fine_amount)
            
            # 기본 조치 정보 구성
            action = {
                'entity_name': entity_name,
                'industry_sector': industry_sector,
                'violation_details': '',  # Rule-based로는 복잡한 위반 내용 추출 어려움
                'action_type': action_type,
                'fine_amount': fine_amount,
                'fine_basis_amount': None,
                'sanction_period': '',
                'sanction_scope': '',
                'effective_date': None
            }
            
            actions.append(action)
            
            logger.info(f"추출된 조치: {action}")
            return actions
            
        except Exception as e:
            logger.error(f"조치 정보 추출 실패: {e}")
            return []
    
    def _classify_industry(self, text: str, entity_name: str) -> str:
        """업권 분류"""
        combined_text = f"{text} {entity_name}".lower()
        
        for industry, keywords in self.patterns['industry_keywords'].items():
            if any(keyword in combined_text for keyword in keywords):
                return industry
        
        return '기타'
    
    def _extract_action_type(self, text: str, fine_amount: Optional[int]) -> str:
        """조치 유형 추출"""
        # 금액이 있으면 과태료/과징금
        if fine_amount:
            if '과징금' in text:
                return '과징금'
            else:
                return '과태료'
        
        # 금액이 없는 경우 다른 조치 유형 찾기
        action_keywords = {
            '직무정지': ['직무정지', '업무정지'],
            '인가': ['인가', '승인', '허가'],
            '재심': ['재심', '직권재심'],
            '취소': ['취소', '철회'],
            '경고': ['경고', '주의'],
            '개선명령': ['개선명령', '시정명령'],
            '업무개선명령': ['업무개선명령']
        }
        
        for action_type, keywords in action_keywords.items():
            if any(keyword in text for keyword in keywords):
                return action_type
        
        return ''
    
    def _extract_fine_amount(self, text: str) -> Optional[int]:
        """과태료/과징금 금액 추출 (수정의결 우선)"""
        # 수정의결 금액 우선 확인
        revised_patterns = [
            r'(\d+(?:,\d{3})*)\s*백만원으로\s*상향',
            r'수정의결.*?(\d+(?:,\d{3})*)\s*백만원',
            r'상향.*?(\d+(?:,\d{3})*)\s*백만원',
            r'수정.*?(\d+(?:,\d{3})*)\s*백만원'
        ]
        
        for pattern in revised_patterns:
            revised_match = re.search(pattern, text)
            if revised_match:
                amount_str = revised_match.group(1).replace(',', '')
                logger.info(f"수정의결 금액 발견: {amount_str}백만원")
                return int(amount_str) * 1000000
        
        # 수정의결이 없으면 일반 금액 패턴 확인
        # 백만원 단위 먼저 확인
        million_match = re.search(self.patterns['amount_million'], text)
        if million_match:
            amount_str = million_match.group(1).replace(',', '')
            return int(amount_str) * 1000000
        
        # 원 단위 확인
        won_match = re.search(self.patterns['amount_won'], text)
        if won_match:
            amount_str = won_match.group(1).replace(',', '')
            return int(amount_str)
        
        return None
    
    def extract_violation_full_text(self, text: str) -> str:
        """조치 이유 전문 추출 (가. 지적사항 섹션)"""
        try:
            violation_match = re.search(self.patterns['violation_section'], text, re.DOTALL | re.IGNORECASE)
            
            if violation_match:
                violation_text = violation_match.group(1).strip()
                logger.info(f"위반 전문 텍스트 추출 성공: {len(violation_text)}자")
                return violation_text
            else:
                logger.warning("위반 전문 텍스트를 찾을 수 없습니다.")
                return ""
        except Exception as e:
            logger.error(f"위반 전문 텍스트 추출 실패: {e}")
            return ""
    
    def extract_target_details(self, text: str) -> Dict[str, Any]:
        """조치대상자 세부 정보 추출"""
        try:
            target_details = {
                'target_type': '',
                'targets': []
            }
            
            # 조치대상자 섹션 찾기
            target_section_match = re.search(self.patterns['target_info_section'], text, re.DOTALL | re.IGNORECASE)
            
            if not target_section_match:
                logger.warning("조치대상자 인적사항 섹션을 찾을 수 없습니다.")
                return target_details
            
            target_section = target_section_match.group(1)
            logger.info(f"조치대상자 섹션 발견: {target_section[:100]}...")
            
            # 각 대상자 유형별로 정보 추출
            for target_type, pattern in self.patterns['target_types'].items():
                matches = re.findall(pattern, target_section)
                if matches:
                    target_details['target_type'] = target_type
                    for match in matches:
                        target_info = {
                            'type': target_type,
                            'description': match.strip()
                        }
                        
                        # 임직원의 경우 직책과 성명 분리 시도
                        if target_type == '임직원' and match.strip():
                            # 예: "㈜아이엠증권 前 상무보대우 甲"
                            parts = match.strip().split()
                            if len(parts) >= 3:
                                target_info['company'] = parts[0]
                                target_info['position'] = ' '.join(parts[1:-1])
                                target_info['name'] = parts[-1]
                        
                        target_details['targets'].append(target_info)
            
            logger.info(f"조치대상자 정보 추출 완료: {target_details}")
            return target_details
            
        except Exception as e:
            logger.error(f"조치대상자 세부 정보 추출 실패: {e}")
            return {'target_type': '', 'targets': []}
    
    def parse_financial_amounts(self, text: str) -> Dict[str, Optional[int]]:
        """금융 금액 파싱"""
        return {
            'fine_amount': self._extract_fine_amount(text),
            'fine_basis_amount': None  # 추가 구현 필요
        }
    
    def extract_full_document_structure(self, text: str, filename: str) -> Dict[str, Any]:
        """전체 문서 구조 추출 (통합 메서드)"""
        try:
            # 메타데이터 추출
            decision_metadata = self.extract_decision_metadata(text, filename)
            
            # 법률 조항 추출
            laws = self.extract_laws_and_articles(text)
            
            # 조치 정보 추출
            actions = self.extract_actions_and_violations(text, filename)
            
            # 위반 전문 추출
            violation_full_text = self.extract_violation_full_text(text)
            
            # 조치대상자 세부 정보 추출
            target_details = self.extract_target_details(text)
            
            # laws를 actions와 연결하고 새로운 필드들 추가
            if actions and laws:
                for action in actions:
                    action['laws_cited'] = laws
                    action['violation_full_text'] = violation_full_text
                    action['target_details'] = target_details
            
            result = {
                'decision': decision_metadata,
                'actions': actions,
                'laws': laws,
                'extraction_method': 'rule_based',
                'confidence_score': 0.95  # Rule-based는 높은 신뢰도
            }
            
            logger.info("Rule-based 추출 완료")
            return result
            
        except Exception as e:
            logger.error(f"전체 문서 구조 추출 실패: {e}")
            raise