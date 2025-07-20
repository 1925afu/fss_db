#!/usr/bin/env python3
"""
DB에 저장된 데이터와 원본 PDF 텍스트 비교 검증 (정수형 금액 비교 포함)
"""

import sys
from pathlib import Path
import random
import PyPDF2
from datetime import datetime
import re

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.fsc_models import Decision, Action, Law, ActionLawMap

def extract_text_from_pdf(pdf_path: str) -> str:
    """PDF에서 텍스트 추출"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(min(10, len(pdf_reader.pages))):  # 처음 10페이지만
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
            return text.strip()
    except Exception as e:
        print(f"PDF 읽기 오류: {e}")
        return ""

def extract_amounts_from_text(text: str) -> list[int]:
    """텍스트에서 모든 금액 추출 (정수형으로 변환)"""
    amounts = []
    
    # 백만원 단위 추출
    million_pattern = r'(\d+(?:,\d{3})*)\s*백만원'
    for match in re.finditer(million_pattern, text):
        amount_str = match.group(1).replace(',', '')
        amounts.append(int(amount_str) * 1000000)
    
    # 만원 단위 추출
    man_pattern = r'(\d+(?:,\d{3})*)\s*만원'
    for match in re.finditer(man_pattern, text):
        amount_str = match.group(1).replace(',', '')
        # 억 단위가 함께 있는지 확인
        if '억' in text[max(0, match.start()-10):match.start()]:
            continue  # 억 단위와 함께 있으면 별도로 처리
        amounts.append(int(amount_str) * 10000)
    
    # 억 단위 + 만원 복합 처리 (예: 46억 5,760만원)
    complex_pattern = r'(\d+)\s*억\s*(\d+(?:,\d{3})*)\s*만원'
    for match in re.finditer(complex_pattern, text):
        uk = int(match.group(1)) * 100000000
        man = int(match.group(2).replace(',', '')) * 10000
        amounts.append(uk + man)
    
    # 원 단위 추출 (큰 숫자만)
    won_pattern = r'(\d{7,}(?:,\d{3})*)\s*원'
    for match in re.finditer(won_pattern, text):
        amount_str = match.group(1).replace(',', '')
        amounts.append(int(amount_str))
    
    return list(set(amounts))  # 중복 제거

def verify_decision_data(decision_id: int, decision_year: int = 2025):
    """특정 의결서 데이터 검증"""
    db = SessionLocal()
    try:
        # 의결서 조회
        decision = db.query(Decision).filter(
            Decision.decision_year == decision_year,
            Decision.decision_id == decision_id
        ).first()
        
        if not decision:
            print(f"의결서 {decision_year}-{decision_id}를 찾을 수 없습니다.")
            return
        
        print(f"\n{'='*80}")
        print(f"의결서 검증: {decision_year}-{decision_id}호")
        print(f"{'='*80}")
        
        # PDF 파일 경로 찾기
        pdf_dir = Path(f"data/processed_pdf/{decision_year}")
        pdf_files = list(pdf_dir.glob(f"*제{decision_year}-{decision_id}호*.pdf"))
        
        if not pdf_files:
            print(f"PDF 파일을 찾을 수 없습니다.")
            return
        
        pdf_path = pdf_files[0]
        print(f"PDF 파일: {pdf_path.name}")
        
        # PDF 텍스트 추출
        pdf_text = extract_text_from_pdf(str(pdf_path))
        
        # PDF에서 모든 금액 추출
        pdf_amounts = extract_amounts_from_text(pdf_text)
        print(f"\nPDF에서 추출된 금액들: {len(pdf_amounts)}개")
        for amount in sorted(pdf_amounts, reverse=True)[:10]:  # 상위 10개만 표시
            print(f"  - {amount:,}원")
        
        # 1. 기본 정보 검증
        print(f"\n[기본 정보 검증]")
        print(f"DB 제목: {decision.title}")
        print(f"DB 날짜: {decision.decision_year}년 {decision.decision_month}월 {decision.decision_day}일")
        print(f"DB 카테고리: {decision.category_1} / {decision.category_2}")
        
        # 제목이 PDF에 있는지 확인
        if decision.title in pdf_text:
            print(f"✅ 제목이 PDF에서 확인됨")
        else:
            print(f"❌ 제목이 PDF에서 확인되지 않음")
        
        # 2. 관련 조치 검증
        actions = db.query(Action).filter(
            Action.decision_year == decision_year,
            Action.decision_id == decision_id
        ).all()
        
        print(f"\n[조치 정보 검증] (총 {len(actions)}개)")
        for idx, action in enumerate(actions, 1):
            print(f"\n조치 {idx}:")
            print(f"  대상: {action.entity_name}")
            print(f"  업권: {action.industry_sector}")
            print(f"  조치유형: {action.action_type}")
            if action.fine_amount:
                print(f"  DB 금액: {action.fine_amount:,}원")
                
                # 정수형으로 금액 비교
                if action.fine_amount in pdf_amounts:
                    print(f"  ✅ 금액이 PDF에서 정확히 확인됨")
                else:
                    # 근사값 확인 (±10% 범위)
                    tolerance = action.fine_amount * 0.1
                    close_amounts = [amt for amt in pdf_amounts 
                                   if abs(amt - action.fine_amount) <= tolerance]
                    if close_amounts:
                        print(f"  ⚠️  근사 금액 발견: {[f'{amt:,}원' for amt in close_amounts]}")
                    else:
                        print(f"  ❌ 금액이 PDF에서 확인되지 않음")
            
            # 대상 이름이 PDF에 있는지 확인
            if action.entity_name in pdf_text:
                print(f"  ✅ 대상 이름이 PDF에서 확인됨")
            else:
                # 이름의 일부분으로 재검색
                name_parts = action.entity_name.split()
                partial_match = any(part in pdf_text for part in name_parts if len(part) > 2)
                if partial_match:
                    print(f"  ⚠️  대상 이름 일부가 PDF에서 확인됨")
                else:
                    print(f"  ❌ 대상 이름이 PDF에서 확인되지 않음")
        
        # 3. 관련 법률 검증
        law_mappings = db.query(ActionLawMap, Law, Action).join(
            Law, ActionLawMap.law_id == Law.law_id
        ).join(
            Action, ActionLawMap.action_id == Action.action_id
        ).filter(
            Action.decision_year == decision_year,
            Action.decision_id == decision_id
        ).all()
        
        print(f"\n[법률 정보 검증] (총 {len(law_mappings)}개 매핑)")
        laws_checked = set()
        for mapping, law, action in law_mappings:
            if law.law_id not in laws_checked:
                laws_checked.add(law.law_id)
                print(f"\n법률: {law.law_name}")
                
                # 법률명이 PDF에 있는지 확인
                if law.law_name in pdf_text or law.law_name.replace(" ", "") in pdf_text:
                    print(f"  ✅ 법률명이 PDF에서 확인됨")
                else:
                    print(f"  ❌ 법률명이 PDF에서 확인되지 않음")
            
            if mapping.article_details:
                print(f"  - 조항: {mapping.article_details}")
                if mapping.article_details in pdf_text:
                    print(f"    ✅ 조항이 PDF에서 확인됨")
                else:
                    print(f"    ❓ 조항이 정확히 일치하지 않음")
        
        # 4. 금액 정합성 요약
        print(f"\n[금액 정합성 요약]")
        db_amounts = [action.fine_amount for action in actions if action.fine_amount]
        matched_amounts = [amt for amt in db_amounts if amt in pdf_amounts]
        print(f"DB 금액 총 {len(db_amounts)}개 중 {len(matched_amounts)}개가 PDF에서 확인됨")
        print(f"정합성: {len(matched_amounts)/len(db_amounts)*100:.1f}%" if db_amounts else "N/A")
        
    finally:
        db.close()

def main():
    """샘플 의결서들을 검증"""
    db = SessionLocal()
    try:
        # 2025년 의결서 중 랜덤하게 5개 선택
        all_decisions = db.query(Decision.decision_id).filter(
            Decision.decision_year == 2025
        ).all()
        
        decision_ids = [d[0] for d in all_decisions]
        sample_ids = random.sample(decision_ids, min(5, len(decision_ids)))
        
        print(f"검증할 의결서 샘플: {sorted(sample_ids)}")
        
        for decision_id in sorted(sample_ids):
            verify_decision_data(decision_id)
            print("\n" + "="*80 + "\n")
            
    finally:
        db.close()

if __name__ == "__main__":
    main()