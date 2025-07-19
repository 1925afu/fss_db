#!/usr/bin/env python3
"""
법제처 API를 사용하여 법률 약칭 업데이트
"""
import requests
import json
import time
import xml.etree.ElementTree as ET
import logging
from typing import Optional
import urllib.parse

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_law_abbreviation(law_name: str) -> Optional[str]:
    """법제처 API로 법률 약칭 조회"""
    try:
        # URL 인코딩
        encoded_name = urllib.parse.quote(law_name)
        url = f"https://www.law.go.kr/DRF/lawSearch.do?OC=1925afu&target=law&type=XML&query={encoded_name}"
        
        # API 요청
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # XML 파싱
        root = ET.fromstring(response.content)
        
        # 결과 확인
        result_code = root.find('resultCode').text
        if result_code != '00':
            logger.warning(f"API 오류: {law_name} - {root.find('resultMsg').text}")
            return None
        
        # 모든 법령 정보 확인
        law_elems = root.findall('law')
        
        for law_elem in law_elems:
            # 법령명 확인
            law_name_elem = law_elem.find('법령명한글')
            if law_name_elem is not None and law_name_elem.text:
                found_law_name = law_name_elem.text.strip()
                
                # 정확히 일치하는 법령만 처리
                # 시행령, 시행규칙이 아닌 경우만 (법률 검색 시 시행령/시행규칙 제외)
                if found_law_name == law_name:
                    # 법령구분 확인 (법률/대통령령/총리령 구분)
                    law_type_elem = law_elem.find('법령구분명')
                    if law_type_elem is not None and law_type_elem.text:
                        law_type = law_type_elem.text.strip()
                        
                        # 검색한 법령의 유형과 일치하는지 확인
                        if ('시행령' in law_name and law_type == '대통령령') or \
                           ('시행규칙' in law_name and law_type == '총리령') or \
                           ('시행령' not in law_name and '시행규칙' not in law_name and law_type == '법률'):
                            
                            # 법령약칭명 추출
                            abbr_elem = law_elem.find('법령약칭명')
                            if abbr_elem is not None and abbr_elem.text:
                                abbreviation = abbr_elem.text.strip()
                                if abbreviation:
                                    logger.info(f"약칭 발견: {law_name} -> {abbreviation}")
                                    return abbreviation
        
        logger.info(f"약칭 없음: {law_name}")
        return None
        
    except Exception as e:
        logger.error(f"API 요청 실패 {law_name}: {e}")
        return None

def main():
    """메인 함수"""
    # 기존 크롤링 데이터 로드
    with open('fsc_laws.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    laws = data['laws']
    logger.info(f"총 {len(laws)}개 법률 약칭 조회 시작")
    
    # 약칭 업데이트
    updated_count = 0
    for i, law in enumerate(laws, 1):
        law_name = law['law_name']
        current_short_name = law.get('law_short_name', '')
        
        logger.info(f"\n[{i}/{len(laws)}] 조회 중: {law_name}")
        
        # API로 약칭 조회
        abbreviation = get_law_abbreviation(law_name)
        
        if abbreviation:
            # 약칭이 현재 값과 다른 경우 업데이트
            if abbreviation != current_short_name:
                law['law_short_name_api'] = abbreviation
                law['law_short_name'] = abbreviation  # API 약칭으로 업데이트
                updated_count += 1
                logger.info(f"  업데이트: {current_short_name} -> {abbreviation}")
            else:
                logger.info(f"  동일: {abbreviation}")
        else:
            # API에서 약칭을 찾지 못한 경우
            law['law_short_name_api'] = None
            logger.info(f"  API 약칭 없음, 기존 유지: {current_short_name}")
        
        # API 부하 방지를 위한 대기
        time.sleep(0.5)
    
    # 결과 저장
    output_file = 'fsc_laws_with_abbreviations.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_count': len(laws),
            'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_count': updated_count,
            'laws': laws
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n약칭 업데이트 완료!")
    logger.info(f"업데이트된 법률: {updated_count}개")
    logger.info(f"결과 저장: {output_file}")
    
    # 통계 출력
    api_found = sum(1 for law in laws if law.get('law_short_name_api') is not None)
    logger.info(f"\nAPI 약칭 발견: {api_found}/{len(laws)}")

if __name__ == "__main__":
    main()