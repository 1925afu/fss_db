#!/usr/bin/env python3
"""
2025년 의결서 파일 배치 처리 (10개씩)
gemini-2.5-flash 모델 사용
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import asyncio

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

from app.services.pdf_processor import PDFProcessor
from app.core.database import get_db
from app.core.config import settings
from app.models.fsc_models import Decision

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'process_2025_batch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def process_batch(pdf_files, processor, batch_num, total_batches):
    """배치 처리 함수"""
    success_count = 0
    fail_count = 0
    
    logger.info(f"\n{'='*60}")
    logger.info(f"배치 {batch_num}/{total_batches} 처리 시작 ({len(pdf_files)}개 파일)")
    logger.info(f"{'='*60}")
    
    for idx, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"\n[배치 {batch_num}] {idx}/{len(pdf_files)}: {pdf_path.name}")
        
        try:
            # PDF 처리
            result = await processor.process_single_pdf(str(pdf_path))
            
            if result:
                success_count += 1
                logger.info(f"✅ 성공: {pdf_path.name}")
            else:
                fail_count += 1
                logger.error(f"❌ 실패: {pdf_path.name}")
                
        except Exception as e:
            fail_count += 1
            logger.error(f"❌ 오류: {pdf_path.name} - {str(e)}")
    
    return success_count, fail_count

async def main():
    # 모델 설정 확인
    logger.info(f"Using GEMINI_MODEL: {settings.GEMINI_MODEL}")
    
    # PDF 디렉토리 설정
    pdf_dir = Path("data/processed_pdf/2025")
    
    if not pdf_dir.exists():
        logger.error(f"Directory not found: {pdf_dir}")
        return
    
    # 데이터베이스 연결 및 PDFProcessor 초기화
    db = next(get_db())
    processor = PDFProcessor(db=db)
    
    # 이미 처리된 의결서 번호 확인
    processed_decisions = db.query(Decision.decision_id).filter(
        Decision.decision_year == 2025
    ).all()
    processed_ids = {d[0] for d in processed_decisions}
    logger.info(f"이미 처리된 의결서: {len(processed_ids)}개")
    
    # 의결서 파일만 선택 (금융위 의결서(제2025-*호) 형식)
    all_pdf_files = list(pdf_dir.glob("금융위 의결서(제2025-*호)*.pdf"))
    
    # 이미 처리된 파일 제외
    pdf_files = []
    for pdf_file in all_pdf_files:
        # 파일명에서 의결번호 추출
        filename = pdf_file.name
        if "제2025-" in filename:
            try:
                decision_num = filename.split("제2025-")[1].split("호")[0]
                decision_id = int(decision_num)
                if decision_id not in processed_ids:
                    pdf_files.append(pdf_file)
            except:
                pdf_files.append(pdf_file)
    
    if not pdf_files:
        logger.info("처리할 새로운 PDF 파일이 없습니다.")
        db.close()
        return
    
    logger.info(f"처리할 PDF 파일: {len(pdf_files)}개")
    
    # 10개씩 배치로 나누기
    batch_size = 10
    batches = [pdf_files[i:i+batch_size] for i in range(0, len(pdf_files), batch_size)]
    total_batches = len(batches)
    
    logger.info(f"총 {total_batches}개 배치로 처리")
    
    # 전체 통계
    total_success = 0
    total_fail = 0
    
    # 각 배치 처리
    for batch_num, batch in enumerate(batches, 1):
        success, fail = await process_batch(batch, processor, batch_num, total_batches)
        total_success += success
        total_fail += fail
        
        # 배치 간 5초 대기 (API 레이트 리밋 고려)
        if batch_num < total_batches:
            logger.info(f"\n배치 {batch_num} 완료. 5초 대기 중...")
            await asyncio.sleep(5)
    
    # 결과 요약
    logger.info(f"\n{'='*60}")
    logger.info("전체 처리 요약")
    logger.info(f"{'='*60}")
    logger.info(f"총 파일: {len(pdf_files)}")
    logger.info(f"성공: {total_success}")
    logger.info(f"실패: {total_fail}")
    logger.info(f"사용 모델: {settings.GEMINI_MODEL}")
    
    # 최종 데이터베이스 상태
    total_decisions = db.query(Decision).filter(Decision.decision_year == 2025).count()
    logger.info(f"\n2025년 총 의결서: {total_decisions}개")
    
    # 데이터베이스 연결 종료
    db.close()

if __name__ == "__main__":
    asyncio.run(main())