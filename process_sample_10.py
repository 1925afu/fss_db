#!/usr/bin/env python3
"""
10개 샘플 PDF 파일 처리 스크립트 (안정적인 배치 처리)
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

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def process_sample_files():
    """10개 샘플 파일 안전 처리"""
    
    # 처리할 샘플 파일 목록
    sample_files = [
        "금융위 의결서(제2025-66호)_한국투자증권㈜에 대한 수시검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2025-69호)_교보증권㈜에 대한 수시검사 결과 조치안(공개용).pdf", 
        "금융위 의결서(제2025-200호)_공인회계사 ☆☆☆에 대한 징계의결안(공개용).pdf",
        "금융위 의결서(제2025-156호)_마운틴자산운용㈜에 대한 수시검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2025-75호)_㈜신한은행에 대한 정기검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2025-49호)_흥국생명보험㈜에 대한 정기검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2025-5호)_00 등 00개 가상자산에 대한 시세조종 금지 위반 조사결과 조치안(공개용).pdf",
        "금융위 의결서(제2025-57호)_(경기)안국저축은행에 대한 수시검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2025-163호)_△△△ 등 11개 가상자산에 대한 시세조종행위 조사결과 조치안(공개용).pdf",
        "금융위 의결서(제2025-120호)_우양에이치씨㈜의 사업보고서 및 감사보고서 등에 대한 조사·감리결과 조치안(공개용).pdf"
    ]
    
    base_path = './data/processed_pdf'
    processing_mode = 'hybrid'  # 하이브리드 모드
    
    print(f"\n=== 샘플 파일 처리 시작 ===")
    print(f"처리 모드: {processing_mode}")
    print(f"총 파일: {len(sample_files)}개")
    
    results = []
    processed_count = 0
    
    for i, filename in enumerate(sample_files, 1):
        file_path = os.path.join(base_path, filename)
        
        # 파일 존재 확인
        if not os.path.exists(file_path):
            print(f"[{i}/{len(sample_files)}] ⚠️  파일 없음: {filename}")
            results.append({
                'filename': filename,
                'success': False,
                'error': 'File not found'
            })
            continue
        
        # 의결번호 추출
        try:
            decision_id = filename.split('제2025-')[1].split('호')[0] if '제2025-' in filename else 'Unknown'
        except:
            decision_id = 'Unknown'
        
        print(f"[{i}/{len(sample_files)}] 제2025-{decision_id}호 처리 중...")
        
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
            
            results.append({
                'filename': filename,
                'decision_id': decision_id,
                'success': result.get('success', False),
                'error': result.get('error', '')
            })
            
        except Exception as e:
            print(f"  ❌ 예외: {str(e)}")
            # 세션 롤백
            try:
                db.rollback()
            except:
                pass
            results.append({
                'filename': filename,
                'decision_id': decision_id,
                'success': False,
                'error': str(e)
            })
        finally:
            # 세션 정리
            try:
                db.close()
            except:
                pass
        
        # 파일 간 짧은 대기 (API 레이트 리밋 고려)
        if i < len(sample_files):
            print(f"  💤 다음 파일을 위해 3초 대기...")
            await asyncio.sleep(3)
    
    # 최종 결과 출력
    print(f"\n=== 처리 완료 ===")
    print(f"성공: {processed_count}/{len(sample_files)} 파일")
    print(f"실패: {len(sample_files) - processed_count} 파일")
    
    if processed_count < len(sample_files):
        print("\n실패한 파일 목록:")
        for result in results:
            if not result['success']:
                print(f"  - 제2025-{result['decision_id']}호: {result['error']}")
    
    # 데이터베이스 현황 확인
    from app.models.fsc_models import Decision, Action, Law
    
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
    
    return processed_count, results

if __name__ == "__main__":
    asyncio.run(process_sample_files())