#!/usr/bin/env python3
"""
남은 샘플 PDF 파일들만 처리하는 스크립트
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.services.pdf_processor import PDFProcessor
from app.core.database import SessionLocal
from app.models.fsc_models import Decision, Action, Law

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def process_remaining_files():
    """남은 샘플 파일들만 처리"""
    
    # 전체 샘플 파일 목록
    all_sample_files = [
        ("156", "금융위 의결서(제2025-156호)_마운틴자산운용㈜에 대한 수시검사 결과 조치안(공개용).pdf"),
        ("75", "금융위 의결서(제2025-75호)_㈜신한은행에 대한 정기검사 결과 조치안(공개용).pdf"),
        ("49", "금융위 의결서(제2025-49호)_흥국생명보험㈜에 대한 정기검사 결과 조치안(공개용).pdf"),
        ("5", "금융위 의결서(제2025-5호)_00 등 00개 가상자산에 대한 시세조종 금지 위반 조사결과 조치안(공개용).pdf"),
        ("57", "금융위 의결서(제2025-57호)_(경기)안국저축은행에 대한 수시검사 결과 조치안(공개용).pdf"),
        ("163", "금융위 의결서(제2025-163호)_△△△ 등 11개 가상자산에 대한 시세조종행위 조사결과 조치안(공개용).pdf"),
        ("120", "금융위 의결서(제2025-120호)_우양에이치씨㈜의 사업보고서 및 감사보고서 등에 대한 조사·감리결과 조치안(공개용).pdf")
    ]
    
    # 이미 처리된 의결서 확인
    db = SessionLocal()
    try:
        existing_ids = set()
        decisions = db.query(Decision).filter(Decision.decision_year == 2025).all()
        for d in decisions:
            existing_ids.add(str(d.decision_id))
            print(f"이미 처리됨: 제2025-{d.decision_id}호")
    finally:
        db.close()
    
    # 처리할 파일 필터링
    files_to_process = []
    for decision_id, filename in all_sample_files:
        if decision_id not in existing_ids:
            files_to_process.append((decision_id, filename))
    
    if not files_to_process:
        print("처리할 새로운 파일이 없습니다.")
        return
    
    print(f"\n처리할 파일: {len(files_to_process)}개")
    for decision_id, filename in files_to_process:
        print(f"  - 제2025-{decision_id}호")
    
    base_path = './data/processed_pdf'
    processing_mode = 'hybrid'  # 하이브리드 모드
    
    results = []
    processed_count = 0
    
    for i, (decision_id, filename) in enumerate(files_to_process, 1):
        file_path = os.path.join(base_path, filename)
        
        # 파일 존재 확인
        if not os.path.exists(file_path):
            print(f"[{i}/{len(files_to_process)}] ⚠️  파일 없음: {filename}")
            continue
        
        print(f"[{i}/{len(files_to_process)}] 제2025-{decision_id}호 처리 중...")
        
        # 각 파일마다 새로운 DB 세션 생성 (오류 격리)
        db = SessionLocal()
        try:
            processor = PDFProcessor(db, use_2_step_pipeline=True, processing_mode=processing_mode)
            result = await processor.process_single_pdf(file_path, processing_mode=processing_mode)
            
            if result.get('success', False):
                print(f"  ✅ 성공")
                processed_count += 1
                
                # 처리 결과 정보 출력
                if result.get('db_result'):
                    db_result = result['db_result']
                    print(f"     - 조치 수: {len(db_result.get('actions_saved', []))}")
                    print(f"     - 법률 수: {db_result.get('laws_saved', 0)}")
            else:
                print(f"  ❌ 실패: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            print(f"  ❌ 예외: {str(e)}")
            try:
                db.rollback()
            except:
                pass
        finally:
            try:
                db.close()
            except:
                pass
        
        # 파일 간 대기 (API 레이트 리밋 고려)
        if i < len(files_to_process):
            print(f"  💤 다음 파일을 위해 5초 대기...")
            await asyncio.sleep(5)
    
    # 최종 결과 출력
    print(f"\n=== 처리 완료 ===")
    print(f"신규 처리 성공: {processed_count}/{len(files_to_process)} 파일")
    
    # 데이터베이스 현황 확인
    
    db = SessionLocal()
    try:
        decision_count = db.query(Decision).count()
        action_count = db.query(Action).count()
        law_count = db.query(Law).count()
        
        print(f"\n=== 데이터베이스 현황 ===")
        print(f"의결서: {decision_count}개")
        print(f"조치: {action_count}개")
        print(f"법률: {law_count}개")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(process_remaining_files())