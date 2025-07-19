#!/usr/bin/env python3
"""
샘플 PDF 파일 10개를 처리하는 스크립트
하이브리드 처리 (Rule-based + AI) 사용
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.pdf_processor import PDFProcessor
from app.core.database import SessionLocal

def process_sample_pdfs():
    """선택된 10개의 샘플 PDF 파일을 처리합니다."""
    
    # 처리할 샘플 PDF 파일 목록
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
    
    # 데이터베이스 세션
    db = SessionLocal()
    
    # PDF 처리기 초기화
    processor = PDFProcessor(db)
    
    print("="*80)
    print("샘플 PDF 파일 처리 시작")
    print("="*80)
    print(f"처리할 파일 수: {len(sample_files)}개")
    print(f"처리 모드: 하이브리드 (Rule-based + AI)")
    print()
    
    # 처리 통계
    success_count = 0
    failed_files = []
    
    for i, filename in enumerate(sample_files, 1):
        print(f"\n[{i}/{len(sample_files)}] 처리 중: {filename}")
        print("-" * 60)
        
        pdf_path = Path("data/processed_pdf") / filename
        
        if not pdf_path.exists():
            print(f"⚠️  파일이 존재하지 않습니다: {pdf_path}")
            failed_files.append(filename)
            continue
        
        try:
            # 하이브리드 모드로 처리 (mode='hybrid')
            import asyncio
            result = asyncio.run(processor.process_single_pdf(str(pdf_path), processing_mode='hybrid'))
            
            if result:
                print("✅ 성공적으로 처리되었습니다.")
                success_count += 1
                
                # 처리 결과 요약 출력
                if result.get('decision'):
                    print(f"   - 의결번호: 제{result['decision']['decision_year']}-{result['decision']['decision_id']}호")
                    print(f"   - 제목: {result['decision'].get('title', 'N/A')}")
                    print(f"   - 카테고리: {result['decision'].get('category_1', 'N/A')} / {result['decision'].get('category_2', 'N/A')}")
                
                if result.get('actions'):
                    print(f"   - 조치 수: {len(result['actions'])}개")
                    for action in result['actions'][:3]:  # 최대 3개만 표시
                        print(f"     • {action.get('entity_name', 'N/A')} - {action.get('action_type', 'N/A')}")
            else:
                print("❌ 처리 실패")
                failed_files.append(filename)
                
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
            failed_files.append(filename)
    
    # 처리 결과 요약
    print("\n" + "="*80)
    print("처리 완료")
    print("="*80)
    print(f"성공: {success_count}/{len(sample_files)} 파일")
    print(f"실패: {len(failed_files)} 파일")
    
    if failed_files:
        print("\n실패한 파일 목록:")
        for f in failed_files:
            print(f"  - {f}")
    
    # 데이터베이스 통계
    from app.models.fsc_models import Decision, Action, Law
    
    decision_count = db.query(Decision).count()
    action_count = db.query(Action).count()
    law_count = db.query(Law).count()
    
    print(f"\n데이터베이스 현황:")
    print(f"  - 의결서: {decision_count}개")
    print(f"  - 조치: {action_count}개")
    print(f"  - 법률: {law_count}개")
    
    db.close()
    
    return success_count, failed_files

if __name__ == "__main__":
    process_sample_pdfs()