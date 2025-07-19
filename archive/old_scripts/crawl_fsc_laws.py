#!/usr/bin/env python3
"""
금융위원회 소관 법규 크롤링 스크립트
https://www.fsc.go.kr/po040101에서 법규 정보를 크롤링하여 저장
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import logging
from typing import List, Dict
import re

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_total_pages(base_url: str) -> int:
    """전체 페이지 수 확인"""
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # board-total-wrap에서 페이지 정보 찾기
        total_wrap = soup.find('div', class_='board-total-wrap')
        if total_wrap:
            # "페이지 1/12" 형식에서 총 페이지 수 추출
            page_text = total_wrap.text
            page_match = re.search(r'페이지\s*\d+/(\d+)', page_text)
            if page_match:
                return int(page_match.group(1))
        
        # paginate에서 마지막 페이지 찾기
        paginate = soup.find('div', class_='paginate')
        if paginate:
            # 마지막 페이지 링크 찾기
            last_link = paginate.find('a', class_='last')
            if last_link and last_link.get('href'):
                last_url = last_link['href']
                page_match = re.search(r'curPage=(\d+)', last_url)
                if page_match:
                    return int(page_match.group(1))
        
        # 페이지 정보를 찾을 수 없으면 1페이지만
        return 1
        
    except Exception as e:
        logger.error(f"페이지 수 확인 실패: {e}")
        return 1

def crawl_laws_page(page_num: int) -> List[Dict]:
    """특정 페이지의 법규 목록 크롤링"""
    url = f"https://www.fsc.go.kr/po040101?curPage={page_num}"
    laws = []
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # board-list-wrap에서 법규 목록 찾기
        board_list = soup.find('div', class_='board-list-wrap')
        if not board_list:
            logger.warning(f"페이지 {page_num}: 목록을 찾을 수 없습니다")
            return laws
        
        # ul > li 구조로 되어 있음
        items = board_list.find('ul').find_all('li')
        for item in items:
            try:
                inner = item.find('div', class_='inner')
                if not inner:
                    continue
                
                # 번호
                count_elem = inner.find('div', class_='count')
                law_no = count_elem.text.strip() if count_elem else ''
                
                # 법규명과 링크
                subject_div = inner.find('div', class_='subject')
                if subject_div:
                    law_link_elem = subject_div.find('a')
                    if law_link_elem:
                        law_name = law_link_elem.text.strip()
                        law_link = law_link_elem.get('href', '')
                        
                        # 정보 추출 (시행일, 법규유형)
                        info_div = inner.find('div', class_='info')
                        law_type = ''
                        effective_date = ''
                        if info_div:
                            spans = info_div.find_all('span')
                            for span in spans:
                                text = span.text.strip()
                                if '시행일' in text:
                                    effective_date = text.replace('시행일 : ', '')
                                elif text in ['법률', '대통령령', '총리령']:
                                    law_type = text
                        
                        # 공포 정보
                        day_div = inner.find('div', class_='day')
                        public_info = ''
                        if day_div:
                            public_info = day_div.text.strip()
                        
                        law_info = {
                            'law_no': law_no,
                            'law_name': law_name,
                            'law_type': law_type,
                            'effective_date': effective_date,
                            'public_info': public_info,
                            'link': law_link
                        }
                        
                        # 약칭 생성
                        law_info['law_short_name'] = generate_short_name(law_name)
                        
                        laws.append(law_info)
                        logger.info(f"추출: {law_name} ({law_type})")
                        
            except Exception as e:
                logger.error(f"항목 처리 중 오류: {e}")
                continue
                
    except Exception as e:
        logger.error(f"페이지 {page_num} 크롤링 실패: {e}")
        
    return laws

def generate_short_name(law_name: str) -> str:
    """법률명에서 약칭 생성"""
    # 괄호 안의 약칭이 있으면 추출
    short_match = re.search(r'[（(]([^）)]+)[）)]', law_name)
    if short_match:
        return short_match.group(1)
    
    # 일반적인 약칭 패턴
    short_names = {
        '자본시장과 금융투자업에 관한 법률': '자본시장법',
        '금융회사의 지배구조에 관한 법률': '지배구조법',
        '주식회사 등의 외부감사에 관한 법률': '외부감사법',
        '신용정보의 이용 및 보호에 관한 법률': '신용정보법',
        '전자금융거래법': '전금법',
        '보험업법': '보험업법',
        '은행법': '은행법',
        '금융실명거래 및 비밀보장에 관한 법률': '금융실명법',
        '가상자산 이용자 보호 등에 관한 법률': '가상자산법'
    }
    
    # 정확한 매칭 확인
    for full_name, short_name in short_names.items():
        if full_name in law_name:
            return short_name
    
    # 시행령/시행규칙 처리
    base_name = law_name
    suffix = ''
    if '시행령' in law_name:
        base_name = law_name.replace(' 시행령', '').replace('시행령', '')
        suffix = ' 시행령'
    elif '시행규칙' in law_name:
        base_name = law_name.replace(' 시행규칙', '').replace('시행규칙', '')
        suffix = ' 시행규칙'
    
    # 약칭이 있으면 사용
    for full_name, short_name in short_names.items():
        if full_name in base_name:
            return short_name + suffix
    
    # 없으면 원래 이름 반환
    return law_name

def main():
    """메인 함수"""
    base_url = "https://www.fsc.go.kr/po040101?curPage=1"
    
    logger.info("금융위원회 소관 법규 크롤링 시작")
    
    # 전체 페이지 수 확인
    total_pages = get_total_pages(base_url)
    logger.info(f"전체 페이지 수: {total_pages}")
    
    all_laws = []
    
    # 각 페이지 크롤링
    for page in range(1, total_pages + 1):
        logger.info(f"\n페이지 {page}/{total_pages} 크롤링 중...")
        laws = crawl_laws_page(page)
        all_laws.extend(laws)
        
        # 서버 부하 방지를 위한 대기
        if page < total_pages:
            time.sleep(1)
    
    # 결과 저장
    output_file = 'fsc_laws.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_count': len(all_laws),
            'crawled_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'laws': all_laws
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n크롤링 완료!")
    logger.info(f"총 {len(all_laws)}개 법규 수집")
    logger.info(f"결과 저장: {output_file}")
    
    # 법규 유형별 통계
    law_types = {}
    for law in all_laws:
        law_type = law['law_type']
        law_types[law_type] = law_types.get(law_type, 0) + 1
    
    logger.info("\n법규 유형별 통계:")
    for law_type, count in sorted(law_types.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {law_type}: {count}개")

if __name__ == "__main__":
    main()