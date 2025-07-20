import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import sys
import os
import PyPDF2

# 상위 디렉토리의 모듈 임포트를 위해 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.law_normalizer import get_law_normalizer

logger = logging.getLogger(__name__)


class RuleBasedExtractor:
    """Rule-based 추출기 - 금융위 의결서 표준 포맷 대응"""
    
    def __init__(self):
        # 법률명 정규화기 초기화
        self.law_normalizer = get_law_normalizer()
        # 정규식 패턴 정의
        self.patterns = {
            # 의결 정보 패턴
            'decision_number': r'제(\d{4})-(\d+)호',
            'decision_date': r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',
            
            # 근거법규 섹션 패턴 (숫자와 한글 기호 모두 지원)
            'law_section': r'(?:\d+\.|[가-하]\.)\s*근거법규(.*?)(?=\d+\.|[가-하]\.|$)',
            
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
            
            # 조치 이유 섹션 패턴 (더 견고한 패턴)
            'violation_section': [
                r'가\.([^나다라마바사아자차카타파하]*?)(?=나\.|\d+\.|$)',  # 가. ~ 나./숫자. 까지
                r'가\.([^가-하]*?)(?=[나-하]\.|\d+\.|$)',  # 가. ~ 다른 한글 기호까지
                r'가\.(.{10,}?)(?=(?:[나-하]\.|\d+\.|4\.|5\.|6\.|7\.|8\.|9\.))',  # 최소 10자 이상
            ],
            
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
            
            # 의결서 PDF에는 날짜 정보가 없으므로 기본값 사용
            # 실제 날짜는 나중에 의결*.pdf 파일에서 추출
            
            # 제목 추출 (파일명에서)
            title_match = re.search(r'_([^_]+?)(?:\(공개용\))?\.pdf$', filename)
            if title_match:
                metadata['title'] = title_match.group(1)
            
            # 기본값 설정
            metadata.setdefault('decision_year', 2024)
            metadata.setdefault('decision_id', 1)
            metadata.setdefault('decision_month', 0)  # 0 = 날짜 정보 없음
            metadata.setdefault('decision_day', 0)  # 0 = 날짜 정보 없음
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
        """근거법규 섹션에서 법률과 조항 추출 (다중 조항 지원)"""
        try:
            laws = []
            
            # 근거법규 섹션 찾기
            law_section_match = re.search(self.patterns['law_section'], text, re.DOTALL | re.IGNORECASE)
            
            if not law_section_match:
                logger.warning("근거법규 섹션을 찾을 수 없습니다.")
                return laws
            
            law_section_text = law_section_match.group(1)
            logger.info(f"근거법규 섹션 발견: {law_section_text[:100]}...")
            
            # 법률명과 조항을 함께 추출 (줄바꿈 무시하고 전체 텍스트에서 추출)
            # 줄바꿈과 불필요한 공백 정리
            cleaned_text = re.sub(r'\s+', ' ', law_section_text.strip())
            
            # 법률명 패턴으로 모든 매칭 찾기
            law_matches = re.finditer(r'[｢「]([^｣」]+)[｣」]\s*([^｢「]*?)(?=[｢「]|$)', cleaned_text)
            
            for match in law_matches:
                law_name = match.group(1).strip()
                article_text = match.group(2).strip()
                
                if not law_name:
                    continue
                
                # 법률명 정규화
                normalized_law_name = self.law_normalizer.normalize_law_name(law_name)
                
                logger.info(f"전체 조항 텍스트: {article_text}")
                
                # 다중 조항 파싱
                parsed_articles = self._parse_multiple_articles(article_text)
                
                if parsed_articles:
                    for article_info in parsed_articles:
                        # 법률 카테고리 결정
                        law_category = self._determine_law_category(law_name)
                        
                        # 원본 법률명과 정규화된 약칭을 구분하여 저장
                        laws.append({
                            'law_name': law_name,  # 원본 법률명 유지
                            'law_short_name': normalized_law_name,  # 정규화된 약칭
                            'law_category': law_category,
                            'article_details': article_info['details'],
                            'article_purpose': ''  # Rule-based로는 내용 요약 어려움
                        })
                else:
                    # 조항이 없는 경우 법률명만 기록
                    law_category = self._determine_law_category(law_name)
                    
                    # 원본 법률명과 정규화된 약칭을 구분하여 저장
                    laws.append({
                        'law_name': law_name,  # 원본 법률명 유지
                        'law_short_name': normalized_law_name,  # 정규화된 약칭
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
    
    def _parse_multiple_articles(self, article_text: str) -> List[Dict[str, str]]:
        """다중 조항 파싱 (예: 제10조제2항 및 제3항, 제19조제1항제2호 및 제3호)"""
        try:
            articles = []
            
            if not article_text:
                return articles
            
            logger.info(f"조항 텍스트 파싱: {article_text}")
            
            # 먼저 쉼표로 구분된 주요 부분들을 분리
            # 예: "제10조제2항 및 제3항, 제19조제1항제2호 및 제3호"
            major_parts = [part.strip() for part in article_text.split(',')]
            
            for part in major_parts:
                if not part:
                    continue
                    
                # "및"으로 연결된 부분들 처리
                # 예: "제10조제2항 및 제3항" -> ["제10조제2항", "제3항"]
                if ' 및 ' in part:
                    sub_parts = [sub_part.strip() for sub_part in part.split(' 및 ')]
                    
                    # 첫 번째 부분에서 기본 조항 정보 추출
                    base_article = self._extract_single_article(sub_parts[0])
                    if base_article:
                        articles.append(base_article)
                    
                    # 나머지 부분들은 축약형이므로 첫 번째 부분의 조항 번호를 상속
                    if base_article and len(sub_parts) > 1:
                        base_article_num = base_article['article_num']
                        
                        for sub_part in sub_parts[1:]:
                            # 축약형 처리 (예: "제3항" -> 같은 조항의 다른 항)
                            expanded_article = self._expand_abbreviated_article(sub_part, base_article_num)
                            if expanded_article:
                                articles.append(expanded_article)
                else:
                    # "및"이 없는 단일 조항
                    single_article = self._extract_single_article(part)
                    if single_article:
                        articles.append(single_article)
            
            logger.info(f"파싱된 조항 수: {len(articles)}")
            for article in articles:
                logger.info(f"  - {article['details']}")
            
            return articles
            
        except Exception as e:
            logger.error(f"다중 조항 파싱 실패: {e}")
            return []
    
    def _extract_single_article(self, text: str) -> Dict[str, str]:
        """단일 조항 추출"""
        try:
            # 조항 패턴 매칭
            article_match = re.search(r'제(\d+)조(?:제(\d+)항)?(?:제(\d+)호)?(?:의\s*(\d+))?', text)
            
            if not article_match:
                return None
            
            article_num = article_match.group(1)
            paragraph = article_match.group(2)
            item = article_match.group(3)
            sub_item = article_match.group(4)
            
            # 조항 세부 사항 조합
            article_details = f"제{article_num}조"
            if paragraph:
                article_details += f" 제{paragraph}항"
            if item:
                article_details += f" 제{item}호"
            if sub_item:
                article_details += f"의 {sub_item}"
            
            return {
                'details': article_details,
                'article_num': article_num,
                'paragraph': paragraph,
                'item': item,
                'sub_item': sub_item
            }
            
        except Exception as e:
            logger.error(f"단일 조항 추출 실패: {e}")
            return None
    
    def _expand_abbreviated_article(self, abbrev_text: str, base_article_num: str) -> Dict[str, str]:
        """축약된 조항을 완전한 형태로 확장"""
        try:
            # 예: "제3항" -> "제10조 제3항" (base_article_num=10인 경우)
            # 또는 "제3호" -> "제10조 제1항 제3호" (base_article_num=10인 경우)
            
            # 완전한 조항이 있는 경우 (예: "제19조제1항제2호")
            full_article_match = re.search(r'제(\d+)조(?:제(\d+)항)?(?:제(\d+)호)?', abbrev_text)
            if full_article_match:
                new_article_num = full_article_match.group(1)
                paragraph = full_article_match.group(2)
                item = full_article_match.group(3)
                
                article_details = f"제{new_article_num}조"
                if paragraph:
                    article_details += f" 제{paragraph}항"
                if item:
                    article_details += f" 제{item}호"
                
                return {
                    'details': article_details,
                    'article_num': new_article_num,
                    'paragraph': paragraph,
                    'item': item,
                    'sub_item': None
                }
            
            # 항만 있는 경우
            paragraph_match = re.search(r'제(\d+)항', abbrev_text)
            if paragraph_match:
                paragraph = paragraph_match.group(1)
                article_details = f"제{base_article_num}조 제{paragraph}항"
                
                return {
                    'details': article_details,
                    'article_num': base_article_num,
                    'paragraph': paragraph,
                    'item': None,
                    'sub_item': None
                }
            
            # 호만 있는 경우 (제2호, 제3호 등)
            item_match = re.search(r'제(\d+)호', abbrev_text)
            if item_match:
                item = item_match.group(1)
                # 기본적으로 제1항을 가정하거나, 이전 컨텍스트에서 항 정보를 가져와야 함
                # 여기서는 단순화하여 처리
                article_details = f"제{base_article_num}조 제1항 제{item}호"
                
                return {
                    'details': article_details,
                    'article_num': base_article_num,
                    'paragraph': '1',
                    'item': item,
                    'sub_item': None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"축약 조항 확장 실패: {e}")
            return None
    
    def _determine_law_category(self, law_name: str) -> str:
        """법률명을 기반으로 카테고리 결정"""
        # 정규화된 법률명으로 카테고리 결정
        normalized_name = self.law_normalizer.normalize_law_name(law_name)
        
        if '은행' in law_name:
            return '은행법'
        elif '보험' in law_name:
            return '보험법'
        elif '자본시장' in law_name or '금융투자' in law_name:
            return '자본시장법'
        elif '지배구조' in law_name:
            return '지배구조법'
        elif '신용정보' in law_name:
            return '신용정보법'
        elif '금융소비자' in law_name:
            return '금융소비자보호법'
        elif '외부감사' in law_name:
            return '외부감사법'
        elif '공인회계사' in law_name:
            return '공인회계사법'
        else:
            return '기타'
    
    def detect_multiple_actions(self, text: str) -> bool:
        """텍스트에서 복수 조치 가능성을 감지"""
        try:
            # 1. 표 형식의 복수 제재대상 확인 (2025-70호 케이스)
            # "제재대상"과 "제재조치" 테이블에서 여러 개체 확인
            if '제재대상' in text and '제재조치' in text:
                # 표 형식에서 과태료/과징금이 여러 개체에 부과되는지 확인
                table_pattern = r'제재대상[\s\S]*?제재조치[\s\S]*?(?=ㅇ|$)'
                table_match = re.search(table_pattern, text)
                if table_match:
                    table_content = table_match.group(0)
                    # 여러 개체에 대한 과태료/과징금 패턴
                    entity_fine_pattern = r'([\w\s\(\)㈜]+(?:前\s*\w+\s*\w+)?)\s*(?:과태료|과징금)\s*[\d,]+\s*(?:백만원|만원|억원)'
                    entity_fines = re.findall(entity_fine_pattern, table_content)
                    if len(entity_fines) >= 2:
                        logger.info(f"표 형식에서 복수 제재대상 감지: {len(entity_fines)}개")
                        return True
            
            # 2. "조치내용" 섹션에서 여러 개의 "ㅇ"로 시작하는 항목 확인
            action_section_pattern = r'조치내용([\s\S]*?)(?=\s*\d+\.\s*조치이유|\s*나\.\s*근거법규|$)'
            action_section_match = re.search(action_section_pattern, text, re.IGNORECASE)
            
            if action_section_match:
                action_content = action_section_match.group(1)
                # "ㅇ"로 시작하는 항목 개수 확인
                bullet_items = re.findall(r'ㅇ\s*[^\n]+', action_content)
                if len(bullet_items) >= 2:
                    logger.info(f"조치내용 섹션에서 복수 항목 감지: {len(bullet_items)}개")
                    # 과징금이 포함된 항목인지 확인
                    fine_count = sum(1 for item in bullet_items if '과징금' in item or '과태료' in item)
                    if fine_count >= 2:
                        logger.info(f"복수 과징금/과태료 항목 감지: {fine_count}개")
                        return True
            
            # 3. 복수 조치를 나타내는 키워드 확인
            multiple_indicators = [
                r'다음\s*각\s*호의\s*자',
                r'아래와\s*같이\s*조치',
                r'각각\s*부과',
                r'다음과\s*같이\s*과[징태]금을\s*부과',
                r'조치대상자별\s*조치내용',
                r'주요골자.*?과[징태]금.*?계'  # 주요골자 테이블에 합계가 있는 경우
            ]
            
            for pattern in multiple_indicators:
                if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                    logger.info(f"복수 조치 키워드 감지: {pattern}")
                    return True
            
            # 3. 여러 금액이 나열되는지 확인 (더 정확한 패턴)
            amount_pattern = r'과[징태]금\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:백만)?원'
            amounts = re.findall(amount_pattern, text)
            
            # 중복 제거하고 유니크한 금액 개수 확인
            unique_amounts = set(amounts)
            if len(unique_amounts) >= 3:  # 3개 이상의 서로 다른 금액
                logger.info(f"복수 금액 감지: {len(unique_amounts)}개의 서로 다른 과징금/과태료")
                return True
            
            # 4. 조치 대상자가 여러 명 나열되는 패턴
            entity_with_fine_pattern = r'(㈜\w+|前?\s*(?:대표이사|담당임원|이사|감사)\s*[★☆◇◆○●□■△▲\w]+|\w+회계법인)\s*\n?\s*-\s*과[징태]금'
            entity_matches = re.findall(entity_with_fine_pattern, text)
            
            if len(entity_matches) >= 2:
                logger.info(f"복수 조치 대상자 감지: {len(entity_matches)}명")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"복수 조치 감지 실패: {e}")
            return False
    
    def extract_actions_and_violations(self, text: str, filename: str = '') -> List[Dict[str, Any]]:
        """조치와 위반 내용 추출 (복수 조치 지원)"""
        try:
            actions = []
            
            # 복수 조치 가능성 감지
            has_multiple_actions = self.detect_multiple_actions(text)
            
            if has_multiple_actions:
                logger.info("복수 조치 감지됨, 복수 조치 추출 시도")
                # 복수 조치 대상 추출 시도
                actions = self._extract_multiple_sanctions(text, filename)
                
                # 복수 조치 추출이 실패한 경우 단일 조치로 fallback
                if not actions:
                    logger.warning("복수 조치 추출 실패, 단일 조치로 처리")
                    single_result = self._extract_single_action(text, filename)
                    if isinstance(single_result, list):
                        actions = single_result
                    else:
                        actions = [single_result]
            else:
                # 단일 조치로 처리
                logger.info("단일 조치로 처리")
                single_result = self._extract_single_action(text, filename)
                # _extract_single_action이 리스트를 반환하는 경우 (복수 조치)
                if isinstance(single_result, list):
                    actions = single_result
                    logger.info(f"단일 조치 처리에서 {len(actions)}개의 조치 추출됨")
                else:
                    actions = [single_result]
            
            logger.info(f"추출된 조치 수: {len(actions)}")
            for action in actions:
                logger.info(f"조치 대상: {action.get('entity_name', 'Unknown')} - 금액: {action.get('fine_amount', 0)}")
            
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
        # 원안/수정안 표 형태 먼저 확인
        table_amount = self._extract_from_revision_table(text)
        if table_amount:
            return table_amount
            
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
        """조치 이유 전문 추출 (가. 지적사항 섹션) - 여러 패턴 시도"""
        try:
            # 여러 패턴을 순서대로 시도
            for i, pattern in enumerate(self.patterns['violation_section']):
                violation_match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                
                if violation_match:
                    violation_text = violation_match.group(1).strip()
                    if len(violation_text) > 10:  # 최소 길이 체크
                        logger.info(f"위반 전문 텍스트 추출 성공 (패턴 {i+1}): {len(violation_text)}자")
                        return violation_text
            
            # 모든 패턴 실패 시 fallback - 간단한 "가." 이후 텍스트 추출
            fallback_match = re.search(r'가\.(.{20,})', text, re.DOTALL | re.IGNORECASE)
            if fallback_match:
                violation_text = fallback_match.group(1).strip()
                # 다음 섹션에서 자르기
                for separator in ['나.', '다.', '라.', '4.', '5.', '근거법규']:
                    if separator in violation_text:
                        violation_text = violation_text[:violation_text.find(separator)].strip()
                        break
                
                if len(violation_text) > 10:
                    logger.info(f"위반 전문 텍스트 fallback 추출 성공: {len(violation_text)}자")
                    return violation_text
            
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
            
            # 복수 조치인 경우 통합 처리
            if len(actions) > 1:
                logger.info(f"복수 조치 감지 ({len(actions)}개), 통합 처리 시작")
                consolidated_action = self._consolidate_multiple_actions(actions)
                actions = [consolidated_action]  # 단일 리스트로 변환
            
            # laws를 actions와 연결하고 새로운 필드들 추가
            if actions and laws:
                for action in actions:
                    action['laws_cited'] = laws
                    action['violation_full_text'] = violation_full_text
                    # target_details는 복수 조치의 경우 이미 설정됨
                    if 'target_details' not in action:
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
    
    def _extract_single_action(self, text: str, filename: str) -> Dict[str, Any]:
        """단일 조치 정보 추출 (기존 로직) - 복수 조치 지원"""
        # 원안/수정안 표가 있는지 확인
        has_revision_table = bool(re.search(r'원안\s*수정안', text))
        
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
        
        # 원안/수정안 표가 있는 경우 복수 조치 추출 시도
        if has_revision_table:
            revision_actions = self._extract_actions_from_revision_table(text)
            if revision_actions:
                # 복수 조치가 있는 경우 리스트로 반환
                actions = []
                for rev_action in revision_actions:
                    action = {
                        'entity_name': entity_name,
                        'industry_sector': industry_sector,
                        'violation_details': '',
                        'action_type': rev_action['action_type'],
                        'fine_amount': rev_action['fine_amount'],
                        'fine_basis_amount': None,
                        'sanction_period': rev_action.get('sanction_period', ''),
                        'sanction_scope': rev_action.get('sanction_scope', ''),
                        'effective_date': None
                    }
                    actions.append(action)
                return actions  # 리스트 반환
        
        # 기존 단일 조치 처리 로직
        # 금액 추출
        fine_amount = self._extract_fine_amount(text)
        
        # 조치 유형 추출
        if has_revision_table:
            action_type = self._extract_action_type_from_revision(text)
        else:
            action_type = self._extract_action_type(text, fine_amount)
        
        # 제재 기간 추출
        if has_revision_table:
            sanction_period = self._extract_sanction_period_from_revision(text)
        else:
            sanction_period = ''
        
        # 기본 조치 정보 구성
        action = {
            'entity_name': entity_name,
            'industry_sector': industry_sector,
            'violation_details': '',  # Rule-based로는 복잡한 위반 내용 추출 어려움
            'action_type': action_type,
            'fine_amount': fine_amount,
            'fine_basis_amount': None,
            'sanction_period': sanction_period,
            'sanction_scope': '',
            'effective_date': None
        }
        
        return action
    
    def _extract_multiple_sanctions(self, text: str, filename: str) -> List[Dict[str, Any]]:
        """복수 조치 정보 추출"""
        actions = []
        
        try:
            # 원안/수정안 표가 있는지 먼저 확인
            has_revision_table = bool(re.search(r'원안\s*수정안', text))
            if has_revision_table:
                logger.info("원안/수정안 표 발견, 단일 조치 처리로 전달")
                # 원안/수정안 표는 _extract_single_action에서 처리
                return []  # 빈 리스트 반환하여 단일 조치 처리로 fallback
            # 1. "조치내용" 섹션에서 추출 (최우선)
            action_section_pattern = r'조치내용([\s\S]*?)(?=\s*\d+\.\s*조치이유|\s*가\.\s*지적사항|$)'
            action_section_match = re.search(action_section_pattern, text, re.IGNORECASE)
            
            if action_section_match:
                action_content = action_section_match.group(1)
                
                # "ㅇ 대상자명\n    - 과징금 금액" 패턴 (백만원 단위 포함)
                action_pattern = r'ㅇ\s*([^\n]+)\s*\n\s*-\s*과[징태]금\s*([\d,\.]+(?:\s*억)?(?:\s*[\d,\.]+)?\s*(?:백만|만)?)\s*원'
                action_matches = re.findall(action_pattern, action_content)
                
                for entity_name, amount_str in action_matches:
                    entity_name = entity_name.strip()
                    # 금액 파싱 개선 (억, 만 단위 처리)
                    fine_amount = self._parse_complex_amount(amount_str)
                    
                    if entity_name and fine_amount:
                        action = {
                            'entity_name': entity_name,
                            'industry_sector': self._classify_industry(text, entity_name),
                            'violation_details': '',
                            'action_type': '과징금' if '과징금' in action_content else '과태료',
                            'fine_amount': fine_amount,
                            'fine_basis_amount': None,
                            'sanction_period': '',
                            'sanction_scope': '',
                            'effective_date': None
                        }
                        actions.append(action)
                        logger.info(f"조치내용 섹션에서 조치 추출: {entity_name} - {fine_amount:,}원")
            
            # 2. 표 형식의 제재대상-제재조치 테이블 처리 (2025-70호 케이스)
            if not actions and '제재대상' in text and '제재조치' in text:
                logger.info("표 형식 제재대상-제재조치 테이블 처리 시도")
                # 표 형식에서 추출
                table_pattern = r'제재대상[\s\S]*?제재조치[\s\S]*?(?=ㅇ\(금감원|$)'
                table_match = re.search(table_pattern, text)
                
                if table_match:
                    table_content = table_match.group(0)
                    # 패턴 1: "유진투자증권㈜...과태료 3,600 백만원"
                    # 패턴 2: "前 영업이사 G1 과태료 15백만원"
                    entity_fine_patterns = [
                        # 기관 + 금액 패턴 (기관 라벨 제거)
                        r'(?:기\s*관\s*)?([\w\s]+㈜)(?:[\s\S]*?)(?:과태료|과징금)\s*([\d,]+)\s*백만원',
                        # 임직원 + 금액 패턴
                        r'(前\s*[\w\s]+\s*[A-Z]\d*)\s*(?:과태료|과징금)\s*([\d,]+)\s*백만원'
                    ]
                    
                    for pattern in entity_fine_patterns:
                        matches = re.findall(pattern, table_content)
                        for entity_name, amount_str in matches:
                            entity_name = entity_name.strip()
                            # "기  관" 같은 불필요한 텍스트 제거
                            entity_name = re.sub(r'^기\s*관\s*', '', entity_name).strip()
                            fine_amount = self._parse_complex_amount(amount_str + '백만원')
                            
                            if entity_name and fine_amount:
                                # 중복 체크
                                if not any(a['entity_name'] == entity_name for a in actions):
                                    action = {
                                        'entity_name': entity_name,
                                        'industry_sector': self._classify_industry(text, entity_name),
                                        'violation_details': '',
                                        'action_type': '과징금' if '과징금' in table_content else '과태료',
                                        'fine_amount': fine_amount,
                                        'fine_basis_amount': None,
                                        'sanction_period': '',
                                        'sanction_scope': '',
                                        'effective_date': None
                                    }
                                    actions.append(action)
                                    logger.info(f"표 형식에서 조치 추출: {entity_name} - {fine_amount:,}원")
            
            # 3. 조치내용 섹션 추출 실패 시 다른 패턴 시도
            if not actions:
                # 주요골자 테이블에서 추출 시도
                table_pattern = r'주요골자.*?과[징태]금.*?\n([\s\S]*?)(?:계|합계)'
                table_match = re.search(table_pattern, text, re.IGNORECASE | re.DOTALL)
                
                if table_match:
                    table_content = table_match.group(1)
                    
                    # 테이블 행 패턴: 대상자 | 금액
                    row_pattern = r'([^\n│|]+?)\s*[│|]\s*([\d,]+)\s*(?:백만)?원'
                    rows = re.findall(row_pattern, table_content)
                    
                    for entity, amount_str in rows:
                        entity_name = entity.strip()
                        fine_amount = self._parse_amount(amount_str + '원')
                        
                        if entity_name and fine_amount:
                            action = {
                                'entity_name': entity_name,
                                'industry_sector': self._classify_industry(text, entity_name),
                                'violation_details': '',
                                'action_type': '과징금' if '과징금' in text else '과태료',
                                'fine_amount': fine_amount,
                                'fine_basis_amount': None,
                                'sanction_period': '',
                                'sanction_scope': '',
                                'effective_date': None
                            }
                            actions.append(action)
                            logger.info(f"테이블에서 조치 추출: {entity_name} - {fine_amount}원")
            
            # 3. 그래도 실패 시 전체 텍스트에서 패턴 검색
            if not actions:
                # 조치대상자별 상세 패턴으로 시도
                # 회사 패턴
                company_pattern = r'(㈜\w+)\s*\n?\s*-?\s*과[징태]금\s*([\d,]+(?:\s*억)?(?:\s*[\d,]+)?\s*(?:만)?)\s*원'
                company_matches = re.findall(company_pattern, text)
                
                # 임원 패턴
                executive_pattern = r'(前?\s*(?:대표이사|담당임원|이사|감사)\s*[★☆◇◆○●□■△▲\w]+)\s*\n?\s*-?\s*과[징태]금\s*([\d,]+(?:\s*억)?(?:\s*[\d,]+)?\s*(?:만)?)\s*원'
                executive_matches = re.findall(executive_pattern, text)
                
                # 회계법인 패턴
                auditor_pattern = r'([◆◇○●□■△▲\w]+회계법인)\s*\n?\s*-?\s*과[징태]금\s*([\d,]+(?:\s*억)?(?:\s*[\d,]+)?\s*(?:만)?)\s*원'
                auditor_matches = re.findall(auditor_pattern, text)
                
                all_matches = company_matches + executive_matches + auditor_matches
                
                for entity_name, amount_str in all_matches:
                    entity_name = entity_name.strip()
                    fine_amount = self._parse_complex_amount(amount_str)
                    
                    if entity_name and fine_amount:
                        # 중복 체크
                        if not any(a['entity_name'] == entity_name for a in actions):
                            action = {
                                'entity_name': entity_name,
                                'industry_sector': self._classify_industry(text, entity_name),
                                'violation_details': '',
                                'action_type': '과징금' if '과징금' in text else '과태료',
                                'fine_amount': fine_amount,
                                'fine_basis_amount': None,
                                'sanction_period': '',
                                'sanction_scope': '',
                                'effective_date': None
                            }
                            actions.append(action)
                            logger.info(f"전체 텍스트에서 조치 추출: {entity_name} - {fine_amount}원")
            
            return actions
            
        except Exception as e:
            logger.error(f"복수 조치 추출 실패: {e}")
            return []
    
    def _extract_from_revision_table(self, text: str) -> Optional[int]:
        """원안/수정안 표 형태에서 금액 추출"""
        try:
            # 원안/수정안 표 패턴
            table_patterns = [
                # 원안 수정안 형태의 표
                r'원안\s*수정안[\s\S]*?과[태징]료\s*([\d,]+)\s*백만원\s*과[태징]료\s*([\d,]+)\s*백만원',
                # 제재조치 표에서 수정안 열
                r'제재조치\s*\n\s*원안\s*수정안[\s\S]*?과[태징]료[^\n]*?\n[^\n]*?과[태징]료\s*([\d,]+)\s*백만원',
            ]
            
            for pattern in table_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # 수정안 금액 (마지막 그룹)
                    if len(match.groups()) >= 2:
                        # 두 개의 금액이 있으면 두 번째(수정안) 사용
                        revised_amount = match.group(2).replace(',', '')
                        logger.info(f"원안/수정안 표에서 수정안 금액 추출: {revised_amount}백만원")
                        return int(revised_amount) * 1000000
                    elif len(match.groups()) >= 1:
                        # 하나의 금액만 있으면 그것을 사용
                        amount = match.group(1).replace(',', '')
                        logger.info(f"표에서 금액 추출: {amount}백만원")
                        return int(amount) * 1000000
            
            # 더 넓은 패턴으로 수정안 금액 찾기
            revision_section = re.search(r'수정안[\s\S]{0,200}?과[태징]료\s*([\d,]+)\s*백만원', text)
            if revision_section:
                amount = revision_section.group(1).replace(',', '')
                logger.info(f"수정안 섹션에서 금액 추출: {amount}백만원")
                return int(amount) * 1000000
                
        except Exception as e:
            logger.debug(f"원안/수정안 표 추출 실패: {e}")
        
        return None
    
    def _extract_action_type_from_revision(self, text: str) -> str:
        """원안/수정안 표에서 조치 유형 추출"""
        try:
            # 수정안 부분에서 조치 유형 찾기
            revision_section = re.search(r'수정안[\s\S]{0,200}', text)
            if revision_section:
                section_text = revision_section.group(0)
                
                # 조치 유형 패턴
                action_patterns = [
                    (r'과태료', '과태료'),
                    (r'과징금', '과징금'),
                    (r'기관경고', '경고'),
                    (r'업무\s*일부\s*정지', '직무정지'),
                    (r'직무정지', '직무정지'),
                    (r'시정명령', '시정명령'),
                    (r'경고', '경고')
                ]
                
                for pattern, action_type in action_patterns:
                    if re.search(pattern, section_text):
                        logger.info(f"수정안에서 조치 유형 추출: {action_type}")
                        return action_type
        except Exception as e:
            logger.debug(f"수정안 조치 유형 추출 실패: {e}")
        
        # 실패 시 기존 방법 사용
        return self._extract_action_type(text)
    
    def _extract_actions_from_revision_table(self, text: str) -> List[Dict[str, Any]]:
        """원안/수정안 표에서 복수 조치 추출"""
        actions = []
        
        try:
            # 수정안 섹션 찾기
            revision_pattern = r'수정안[\s\S]{0,500}'
            revision_match = re.search(revision_pattern, text)
            
            if revision_match:
                revision_text = revision_match.group(0)
                logger.info("수정안 섹션에서 복수 조치 추출 시작")
                
                # 1. 기관경고 확인
                if re.search(r'기관\s*경고', revision_text):
                    actions.append({
                        'action_type': '경고',
                        'fine_amount': 0,
                        'sanction_period': '',
                        'sanction_scope': ''
                    })
                    logger.info("기관경고 조치 추출")
                
                # 2. 과태료 금액 추출 (수정안에서 마지막 과태료 금액 찾기)
                # 공백을 포함한 더 정확한 패턴 사용
                fine_matches = re.findall(r'과태료\s*([\d,]+)\s*백만원', revision_text)
                if fine_matches:
                    # 감경 금액이 아닌 실제 과태료 금액만 추출
                    # "감경(XXX백만원" 패턴은 제외
                    valid_amounts = []
                    for i, match in enumerate(fine_matches):
                        # 해당 매치 주변 텍스트 확인
                        start_pos = revision_text.find(match)
                        if start_pos > 0:
                            context = revision_text[max(0, start_pos-20):start_pos+50]
                            if '감경(' not in context:
                                valid_amounts.append(match)
                    
                    if valid_amounts:
                        # 마지막 유효한 매치가 수정안의 금액
                        amount = int(valid_amounts[-1].replace(',', '')) * 1000000
                    else:
                        # 유효한 금액이 없으면 원래 로직 사용
                        amount = int(fine_matches[-1].replace(',', '')) * 1000000
                    actions.append({
                        'action_type': '과태료',
                        'fine_amount': amount,
                        'sanction_period': '',
                        'sanction_scope': ''
                    })
                    logger.info(f"과태료 조치 추출: {amount:,}원")
                
                # 3. 과징금 금액 추출
                penalty_match = re.search(r'과징금\s*([\d,]+)\s*백만원', revision_text)
                if penalty_match:
                    amount = int(penalty_match.group(1).replace(',', '')) * 1000000
                    actions.append({
                        'action_type': '과징금',
                        'fine_amount': amount,
                        'sanction_period': '',
                        'sanction_scope': ''
                    })
                    logger.info(f"과징금 조치 추출: {amount:,}원")
                
                # 4. 업무정지 기간 추출 (기관경고가 없는 경우에만)
                if not any(a['action_type'] == '경고' for a in actions):
                    suspension_match = re.search(r'업무\s*(?:일부\s*)?정지\s*(\d+)\s*개?월', revision_text)
                    if suspension_match:
                        period = f"{suspension_match.group(1)}개월"
                        actions.append({
                            'action_type': '직무정지',
                            'fine_amount': 0,
                            'sanction_period': period,
                            'sanction_scope': '업무 일부정지'
                        })
                        logger.info(f"업무정지 조치 추출: {period}")
                
        except Exception as e:
            logger.error(f"원안/수정안 표 복수 조치 추출 실패: {e}")
        
        return actions
    
    def _extract_sanction_period_from_revision(self, text: str) -> str:
        """원안/수정안 표에서 제재 기간 추출"""
        try:
            # 수정안 부분에서 기간 찾기
            revision_section = re.search(r'수정안[\s\S]{0,200}', text)
            if revision_section:
                section_text = revision_section.group(0)
                
                # 기간 패턴
                period_patterns = [
                    r'(\d+)\s*개?월',
                    r'(\d+)\s*년',
                    r'(\d+)\s*일'
                ]
                
                for pattern in period_patterns:
                    match = re.search(pattern, section_text)
                    if match:
                        period = match.group(0)
                        logger.info(f"수정안에서 제재 기간 추출: {period}")
                        return period
        except Exception as e:
            logger.debug(f"수정안 제재 기간 추출 실패: {e}")
        
        # 실패 시 기존 방법 사용
        return self._extract_sanction_period(text)

    def _parse_amount(self, amount_str: str) -> Optional[int]:
        """금액 문자열을 숫자로 변환"""
        if not amount_str:
            return None
        
        try:
            # 숫자만 추출
            numbers = re.findall(r'\d+', str(amount_str).replace(',', ''))
            if not numbers:
                return None
            
            amount = int(numbers[0])
            
            # 단위 처리
            if '백만' in str(amount_str):
                amount *= 1000000
            elif '천만' in str(amount_str):
                amount *= 10000000
            elif '억' in str(amount_str):
                amount *= 100000000
            elif '만' in str(amount_str) and '백만' not in str(amount_str) and '천만' not in str(amount_str):
                amount *= 10000
            elif '천' in str(amount_str) and '천만' not in str(amount_str):
                amount *= 1000
            
            return amount
            
        except Exception as e:
            logger.error(f"금액 파싱 실패: {amount_str} - {e}")
            return None
    
    def _parse_complex_amount(self, amount_str: str) -> Optional[int]:
        """복잡한 금액 문자열을 숫자로 변환 (예: '46억 5,760 만원', '9.8백만원')"""
        if not amount_str:
            return None
        
        try:
            amount_str = amount_str.strip()
            total = 0
            
            # 백만원 단위 처리 (예: 9.8백만원)
            if '백만' in amount_str:
                # 백만 앞의 숫자 추출 (소수점 포함)
                baek_match = re.search(r'([\d,\.]+)\s*백만', amount_str)
                if baek_match:
                    baek = float(baek_match.group(1).replace(',', ''))
                    total = int(baek * 1000000)
                    logger.debug(f"백만원 단위 파싱: '{amount_str}' -> {total:,}원")
                    return total
            
            # 억 단위 처리
            if '억' in amount_str:
                parts = amount_str.split('억')
                if len(parts) >= 1 and parts[0].strip():
                    # 억 앞의 숫자 추출
                    eok_match = re.search(r'([\d,]+)\s*$', parts[0])
                    if eok_match:
                        eok = int(eok_match.group(1).replace(',', ''))
                        total += eok * 100000000
                
                # 억 뒤의 만원 처리
                if len(parts) >= 2:
                    amount_str = parts[1]
            
            # 만원 단위 처리
            if '만' in amount_str and '백만' not in amount_str:
                # 만 앞의 숫자 추출
                man_match = re.search(r'([\d,]+)\s*만', amount_str)
                if man_match:
                    man = int(man_match.group(1).replace(',', ''))
                    total += man * 10000
            # 만이 없고 숫자만 있는 경우 (원 단위)
            elif total == 0:
                numbers = re.findall(r'[\d,]+', amount_str)
                if numbers:
                    total = int(numbers[0].replace(',', ''))
            
            logger.debug(f"금액 파싱: '{amount_str}' -> {total:,}원")
            return total
            
        except Exception as e:
            logger.error(f"복잡한 금액 파싱 실패: {amount_str} - {e}")
            return None
    
    def _consolidate_multiple_actions(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """복수 조치를 하나의 통합 action으로 변환"""
        if not actions or len(actions) <= 1:
            return actions[0] if actions else {}
        
        try:
            # 첫 번째 action(주로 기관)을 기준으로 설정
            primary_action = actions[0]
            total_fine = sum(action.get('fine_amount', 0) for action in actions)
            
            # entity_name 생성: "주요대상 외 N인"
            primary_entity = primary_action.get('entity_name', '')
            other_count = len(actions) - 1
            consolidated_entity_name = f"{primary_entity} 외 {other_count}인"
            
            # target_details 구성
            target_details = {
                'type': 'multiple_sanctions',
                'total_count': len(actions),
                'primary_entity': primary_entity,
                'total_fine': total_fine,
                'targets': []
            }
            
            # 각 대상자 정보를 targets에 추가
            for i, action in enumerate(actions):
                target_info = {
                    'entity_name': action.get('entity_name', ''),
                    'entity_type': self._determine_entity_type(action.get('entity_name', '')),
                    'fine_amount': action.get('fine_amount', 0),
                    'is_primary': i == 0
                }
                
                # 업권 정보 추가 (회계법인인 경우)
                if '회계법인' in action.get('entity_name', ''):
                    target_info['industry_sector'] = '회계/감사'
                elif i == 0:  # 주요 대상자인 경우
                    target_info['industry_sector'] = action.get('industry_sector', '기타')
                
                # 직책 정보 추가 (임직원인 경우)
                entity_name = action.get('entity_name', '')
                if '대표이사' in entity_name or '임원' in entity_name or '이사' in entity_name:
                    # 직책 추출
                    position_match = re.search(r'(前?\s*(?:대표이사|담당임원|이사|감사))', entity_name)
                    if position_match:
                        target_info['position'] = position_match.group(1).strip()
                
                target_details['targets'].append(target_info)
            
            # 통합 action 생성
            consolidated_action = {
                'entity_name': consolidated_entity_name,
                'industry_sector': primary_action.get('industry_sector', '기타'),  # 주요 대상의 업권
                'violation_details': primary_action.get('violation_details', ''),
                'action_type': primary_action.get('action_type', ''),  # 과징금, 과태료 등
                'fine_amount': total_fine,
                'fine_basis_amount': None,
                'sanction_period': '',
                'sanction_scope': '',
                'effective_date': None,
                'target_details': target_details
            }
            
            logger.info(f"복수 조치 통합 완료: {consolidated_entity_name} - 총 {total_fine:,}원")
            return consolidated_action
            
        except Exception as e:
            logger.error(f"복수 조치 통합 실패: {e}")
            # 실패 시 첫 번째 action 반환
            return actions[0] if actions else {}
    
    def _determine_entity_type(self, entity_name: str) -> str:
        """대상자 이름으로부터 유형을 판단"""
        if '㈜' in entity_name or '주식회사' in entity_name:
            return '기관'
        elif '회계법인' in entity_name:
            return '외부감사인'
        elif any(keyword in entity_name for keyword in ['대표이사', '임원', '이사', '감사']):
            return '임직원'
        else:
            return '기타'
    
    def extract_date_from_companion_file(self, decision_year: int, decision_id: int, processed_pdf_dir: str) -> Optional[Tuple[int, int, int]]:
        """의결XXX.pdf 파일에서 날짜 정보를 추출합니다."""
        try:
            # 연도별 디렉토리 경로
            year_dir = os.path.join(processed_pdf_dir, str(decision_year))
            if not os.path.exists(year_dir):
                logger.warning(f"연도 디렉토리가 없습니다: {year_dir}")
                return None
            
            # 의결XXX. 형식의 파일 찾기
            pattern = f'의결{decision_id:03d}\\.'  # 의결048. 형식
            companion_file = None
            
            for filename in os.listdir(year_dir):
                if re.match(pattern, filename) and filename.endswith('.pdf'):
                    companion_file = filename
                    break
            
            if not companion_file:
                # 3자리가 아닌 경우도 시도 (의결48. 형식)
                pattern = f'의결{decision_id}\\.'
                for filename in os.listdir(year_dir):
                    if re.match(pattern, filename) and filename.endswith('.pdf'):
                        companion_file = filename
                        break
            
            if not companion_file:
                logger.debug(f"의결{decision_id}번에 해당하는 의결*.pdf 파일을 찾을 수 없습니다.")
                return None
            
            # PDF에서 날짜 추출
            pdf_path = os.path.join(year_dir, companion_file)
            date_info = self._extract_date_from_pdf(pdf_path)
            
            if date_info:
                logger.info(f"날짜 추출 성공: {decision_year}-{decision_id}호 -> {date_info[0]}년 {date_info[1]}월 {date_info[2]}일")
                return date_info
            else:
                logger.warning(f"날짜 추출 실패: {companion_file}")
                return None
                
        except Exception as e:
            logger.error(f"의결 파일에서 날짜 추출 중 오류: {e}")
            return None
    
    def _extract_date_from_pdf(self, pdf_path: str) -> Optional[Tuple[int, int, int]]:
        """PDF 파일에서 의결일자를 추출합니다."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ''
                # 첫 3페이지만 읽어서 날짜 정보 추출
                for page_num, page in enumerate(reader.pages[:3]):
                    text += page.extract_text()
            
            # 날짜 패턴들 (update_decision_dates.py에서 가져옴)
            date_patterns = [
                # 의결연월일 2025. 3.19. (제5차) 패턴
                r'의결\s*연월일\s*(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*\(제(\d+)차\)',
                # 의결일: 2025. 1. 8
                r'의결일\s*[:：]\s*(\d{4})[\.\년]\s*(\d{1,2})[\.\월]\s*(\d{1,2})',
                # 의결일자: 2025년 1월 8일
                r'의결일자\s*[:：]\s*(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',
                # 2025년 1월 8일 (문서 상단에 있는 경우)
                r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일.*?의결',
                # 2025. 1. 8. (일반 날짜 형식)
                r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.',
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, text[:1000])  # 문서 앞부분에서만 검색
                if match:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    return (year, month, day)
            
            return None
            
        except Exception as e:
            logger.error(f"PDF 텍스트 추출 실패 {pdf_path}: {e}")
            return None