#!/usr/bin/env python3
"""
단일 PDF 파일 처리 스크립트
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

async def process_single_file(filename: str):
    """단일 파일 처리"""
    
    base_path = './data/processed_pdf'
    processing_mode = 'hybrid'
    
    file_path = os.path.join(base_path, filename)
    
    # 파일 존재 확인
    if not os.path.exists(file_path):
        print(f"⚠️  파일 없음: {filename}")
        return False
    
    # 의결번호 추출
    try:
        decision_id = filename.split('제2025-')[1].split('호')[0] if '제2025-' in filename else 'Unknown'
    except:
        decision_id = 'Unknown'
    
    print(f"제2025-{decision_id}호 처리 시작...")
    print(f"파일: {filename}")
    print(f"모드: {processing_mode}")
    print("="*60)
    
    # 새로운 DB 세션 생성
    db = SessionLocal()
    try:
        processor = PDFProcessor(db, use_2_step_pipeline=True, processing_mode=processing_mode)
        result = await processor.process_single_pdf(file_path, processing_mode=processing_mode)
        
        if result.get('success', False):
            print("✅ 처리 성공!")
            
            # 처리 결과 정보 출력
            if result.get('db_result'):
                db_result = result['db_result']
                print(f"   📄 의결서 저장됨")
                print(f"   ⚖️  조치 수: {len(db_result.get('actions_saved', []))}")
                print(f"   📚 법률 수: {db_result.get('laws_saved', 0)}")
                
                # 조치 세부 정보
                for i, action in enumerate(db_result.get('actions_saved', []), 1):
                    action_type = action.get('action_type', 'N/A')
                    entity_name = action.get('entity_name', 'N/A')
                    fine_amount = action.get('fine_amount', 0)
                    fine_str = f"{fine_amount:,}원" if fine_amount else "없음"
                    print(f"     {i}. {entity_name} - {action_type} (과태료: {fine_str})")
            
            return True
        else:
            print(f"❌ 처리 실패: {result.get('error', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"❌ 예외 발생: {str(e)}")
        try:
            db.rollback()
        except:
            pass
        return False
    finally:
        try:
            db.close()
        except:
            pass

async def main():
    """메인 함수"""
    if len(sys.argv) != 2:
        print("사용법: python3 process_single_pdf.py <filename>")
        print("예시: python3 process_single_pdf.py '금융위 의결서(제2025-5호)_*.pdf'")
        return
    
    filename = sys.argv[1]
    
    # 현재 DB 상태 확인
    db = SessionLocal()
    try:
        decision_count = db.query(Decision).count()
        action_count = db.query(Action).count()
        law_count = db.query(Law).count()
        
        print(f"현재 DB 상태:")
        print(f"  - 의결서: {decision_count}개")
        print(f"  - 조치: {action_count}개")
        print(f"  - 법률: {law_count}개")
        print()
    finally:
        db.close()
    
    # 파일 처리
    success = await process_single_file(filename)
    
    # 처리 후 DB 상태 확인
    db = SessionLocal()
    try:
        decision_count_after = db.query(Decision).count()
        action_count_after = db.query(Action).count()
        law_count_after = db.query(Law).count()
        
        print(f"\n처리 후 DB 상태:")
        print(f"  - 의결서: {decision_count_after}개 (+{decision_count_after - decision_count})")
        print(f"  - 조치: {action_count_after}개 (+{action_count_after - action_count})")
        print(f"  - 법률: {law_count_after}개 (+{law_count_after - law_count})")
    finally:
        db.close()
    
    if success:
        print("\n🎉 처리 완료!")
    else:
        print("\n💥 처리 실패!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())