#!/usr/bin/env python3
"""
2025년 의결서 배치 처리 스크립트 (Rate Limit 고려)
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

async def process_files_safely(files, start_idx=0, batch_size=5, processing_mode='rule-based'):
    """안전한 파일 배치 처리 (개별 파일당 새로운 세션)"""
    
    base_path = '/mnt/c/Users/1925a/Documents/fss_db/data/processed_pdf'
    total_files = len(files)
    
    print(f"\n=== 배치 처리 시작 ===")
    print(f"처리 모드: {processing_mode}")
    print(f"총 파일: {total_files}개")
    print(f"배치 크기: {batch_size}개")
    print(f"시작 인덱스: {start_idx}")
    
    results = []
    processed_count = 0
    
    for i in range(start_idx, total_files, batch_size):
        batch = files[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_files + batch_size - 1) // batch_size
        
        print(f"\n--- 배치 {batch_num}/{total_batches} 시작 ({len(batch)}개 파일) ---")
        
        for j, filename in enumerate(batch):
            file_path = os.path.join(base_path, filename)
            file_num = i + j + 1
            
            # 의결번호 추출
            decision_id = filename.split('제2025-')[1].split('호')[0] if '제2025-' in filename else 'Unknown'
            
            print(f"[{file_num}/{total_files}] 제2025-{decision_id}호 처리 중...")
            
            # 각 파일마다 새로운 DB 세션 생성 (오류 격리)
            db = SessionLocal()
            try:
                processor = PDFProcessor(db, use_2_step_pipeline=True, processing_mode=processing_mode)
                result = await processor.process_single_pdf(file_path, processing_mode=processing_mode)
                
                if result['success']:
                    print(f"  ✅ 성공")
                    processed_count += 1
                else:
                    print(f"  ❌ 실패: {result.get('error', 'Unknown error')}")
                
                results.append({
                    'filename': filename,
                    'decision_id': decision_id,
                    'success': result['success'],
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
        
        # 배치 완료 후 잠시 대기 (AI 처리의 경우)
        if processing_mode == 'hybrid' and i + batch_size < total_files:
            print(f"  💤 다음 배치를 위해 10초 대기...")
            await asyncio.sleep(10)
    
    # 최종 결과 요약
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"\n=== 처리 완료 ===")
    print(f"총 처리: {len(results)}개")
    print(f"성공: {successful}개 ({successful/len(results)*100:.1f}%)")
    print(f"실패: {failed}개")
    
    if failed > 0:
        print(f"\n=== 실패 파일 목록 ===")
        for r in results:
            if not r['success']:
                print(f"❌ 제2025-{r['decision_id']}호: {r['error']}")
    
    return results

async def main():
    # 2025년 파일 목록 가져오기
    pdf_dir = '/mnt/c/Users/1925a/Documents/fss_db/data/processed_pdf'
    all_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
    year_2025_files = [f for f in all_files if '금융위 의결서' in f and '제2025-' in f]
    year_2025_files.sort()  # 파일명으로 정렬
    
    print(f"2025년 금융위 의결서 파일: {len(year_2025_files)}개")
    
    # Rule-based 모드로 전체 처리
    results = await process_files_safely(
        year_2025_files, 
        start_idx=0, 
        batch_size=10,  # Rule-based는 빠르므로 10개씩
        processing_mode='rule-based'
    )
    
    return results

if __name__ == '__main__':
    results = asyncio.run(main())