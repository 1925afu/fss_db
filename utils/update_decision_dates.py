#!/usr/bin/env python3
"""
의결*.pdf 파일에서 날짜 정보를 추출하여 데이터베이스를 업데이트하는 스크립트
금융위 의결서 파일과 의결 파일을 매칭하여 정확한 날짜 정보를 업데이트합니다.
"""

import os
import re
import sqlite3
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_date_from_text(text):
    """텍스트에서 의결일자를 추출합니다."""
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
        match = re.search(pattern, text[:1000])  # 문서 앞부분에서만 검색
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            return year, month, day
    
    return None, None, None

def get_decision_number_from_filename(filename):
    """파일명에서 의결번호를 추출합니다."""
    # 의결103. 리딩자산운용㈜... -> 103
    match = re.match(r'의결(\d+)\.', filename)
    if match:
        return int(match.group(1))
    return None

def get_entity_name_from_filename(filename):
    """파일명에서 기관명을 추출합니다."""
    # 의결103. 리딩자산운용㈜에 대한... -> 리딩자산운용㈜
    match = re.match(r'의결\d+\.\s*([^에]+?)(?:에\s*대한|의\s*)', filename)
    if match:
        return match.group(1).strip()
    return None

def read_pdf_text(pdf_path):
    """PDF 파일의 텍스트를 읽습니다."""
    try:
        import PyPDF2
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ''
            # 첫 3페이지만 읽어서 날짜 정보 추출
            for page_num, page in enumerate(reader.pages[:3]):
                text += page.extract_text()
            return text
    except Exception as e:
        logger.error(f"PDF 텍스트 추출 실패 {pdf_path}: {e}")
        return ""

def match_decision_files(processed_pdf_dir):
    """의결 파일과 금융위 의결서 파일을 매칭합니다."""
    matches = []
    
    # 모든 의결*.pdf 파일 찾기
    decision_files = [f for f in os.listdir(processed_pdf_dir) if f.startswith('의결') and f.endswith('.pdf')]
    
    for decision_file in decision_files:
        decision_number = get_decision_number_from_filename(decision_file)
        entity_name = get_entity_name_from_filename(decision_file)
        
        if not decision_number:
            continue
        
        # 매칭되는 금융위 의결서 파일 찾기
        # 패턴: 금융위 의결서(제2025-X호)_...
        pattern = f'금융위 의결서\\(제\\d{{4}}-{decision_number}호\\)'
        
        matching_files = [f for f in os.listdir(processed_pdf_dir) 
                         if re.search(pattern, f) and f.endswith('.pdf')]
        
        if matching_files:
            # 기관명으로 추가 검증
            if entity_name:
                for mf in matching_files:
                    if entity_name in mf:
                        matches.append({
                            'decision_file': decision_file,
                            'fsc_file': mf,
                            'decision_number': decision_number,
                            'entity_name': entity_name
                        })
                        break
            else:
                # 기관명이 없으면 첫 번째 매칭 사용
                matches.append({
                    'decision_file': decision_file,
                    'fsc_file': matching_files[0],
                    'decision_number': decision_number,
                    'entity_name': entity_name or ''
                })
    
    return matches

def update_database_dates(db_path, processed_pdf_dir):
    """데이터베이스의 날짜 정보를 업데이트합니다."""
    
    # 파일 매칭
    matches = match_decision_files(processed_pdf_dir)
    logger.info(f"총 {len(matches)}개의 매칭을 찾았습니다.")
    
    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    updated_count = 0
    
    for match in matches:
        decision_number = match['decision_number']
        decision_file_path = os.path.join(processed_pdf_dir, match['decision_file'])
        
        # 의결 파일에서 실제 날짜 추출
        pdf_text = read_pdf_text(decision_file_path)
        year, month, day = extract_date_from_text(pdf_text)
        
        if not year:
            logger.warning(f"날짜 추출 실패: {match['decision_file']}")
            continue
        
        if year and month and day:
            # FSC 파일명에서 연도와 의결번호 추출
            fsc_match = re.search(r'제(\d{4})-(\d+)호', match['fsc_file'])
            if fsc_match:
                decision_year = int(fsc_match.group(1))
                decision_id = int(fsc_match.group(2))
                
                # 데이터베이스 업데이트
                cursor.execute("""
                    UPDATE decisions 
                    SET decision_month = ?, decision_day = ?
                    WHERE decision_year = ? AND decision_id = ?
                """, (month, day, decision_year, decision_id))
                
                if cursor.rowcount > 0:
                    updated_count += 1
                    logger.info(f"업데이트: {decision_year}-{decision_id}호 -> {year}년 {month}월 {day}일")
    
    # 커밋
    conn.commit()
    
    # 업데이트 결과 확인
    cursor.execute("""
        SELECT decision_year, decision_month, decision_day, COUNT(*) as count
        FROM decisions
        GROUP BY decision_year, decision_month, decision_day
        ORDER BY decision_year DESC, decision_month DESC, decision_day DESC
    """)
    
    print("\n=== 업데이트 후 날짜별 분포 ===")
    for row in cursor.fetchall():
        print(f"{row[0]}년 {row[1]}월 {row[2]}일: {row[3]}건")
    
    conn.close()
    
    logger.info(f"총 {updated_count}개의 의결서 날짜를 업데이트했습니다.")

def main():
    """메인 함수"""
    db_path = "./fss_db.sqlite"
    processed_pdf_dir = "./data/processed_pdf"
    
    # 날짜 업데이트 실행
    update_database_dates(db_path, processed_pdf_dir)

if __name__ == "__main__":
    main()