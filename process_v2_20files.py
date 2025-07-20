#!/usr/bin/env python3
"""
V2 시스템용 PDF 20개 추가 처리 스크립트
- Gemini Structured Output 사용
- 이미 처리된 파일 제외
- 문제 파일(54호, 94호) 제외
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import asyncio

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(str(Path(__file__).parent))

from app.services.pdf_processor_v2 import PDFProcessorV2
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.fsc_models_v2 import DecisionV2

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'process_v2_20files_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 문제가 발생한 파일들 (건너뛸 파일)
SKIP_FILES = {
    "금융위 의결서(제2025-54호)_㈜OOOO의 사업보고서 및 연결감사보고서 등에 대한 조사·감리결과 조치안(공개용).pdf",
    "금융위 의결서(제2025-94호)_신한라이프생명보험㈜에 대한 정기검사 결과 조치안(공개용).pdf"
}

async def process_single_file(pdf_path: Path) -> tuple[bool, str]:
    """개별 파일 처리 (새 세션 사용)"""
    try:
        processor = PDFProcessorV2()  # db_path는 기본값 사용
        
        # 타임아웃 설정 (3분)
        result = await asyncio.wait_for(
            processor.process_single_pdf(str(pdf_path)),
            timeout=180.0
        )
        
        if result:
            return True, "성공"
        else:
            return False, "처리 실패"
            
    except asyncio.TimeoutError:
        return False, "타임아웃 (3분 초과)"
    except Exception as e:
        return False, f"오류: {str(e)[:100]}"

async def main():
    # 모델 설정 확인
    logger.info(f"Using GEMINI_MODEL: {settings.GEMINI_MODEL}")
    logger.info("V2 처리 시스템 사용 (Gemini Structured Output)")
    
    # PDF 디렉토리 설정
    pdf_dir = Path("data/processed_pdf/2025")
    
    if not pdf_dir.exists():
        logger.error(f"Directory not found: {pdf_dir}")
        return
    
    # 이미 V2로 처리된 의결서 번호 확인
    db = SessionLocal()
    try:
        processed_decisions = db.query(DecisionV2.decision_id).filter(
            DecisionV2.decision_year == 2025
        ).all()
        processed_ids = {d[0] for d in processed_decisions}
        logger.info(f"V2에 이미 처리된 의결서: {len(processed_ids)}개")
        logger.info(f"처리된 번호: {sorted(processed_ids)}")
    finally:
        db.close()
    
    # 의결서 파일만 선택 (금융위 의결서(제2025-*호) 형식)
    all_pdf_files = list(pdf_dir.glob("금융위 의결서(제2025-*호)*.pdf"))
    logger.info(f"전체 2025년 의결서 파일: {len(all_pdf_files)}개")
    
    # 이미 처리된 파일과 문제 파일 제외
    pdf_files = []
    skipped_count = 0
    already_processed = 0
    
    for pdf_file in all_pdf_files:
        # 문제 파일 건너뛰기
        if pdf_file.name in SKIP_FILES:
            logger.warning(f"문제 파일 건너뜀: {pdf_file.name}")
            skipped_count += 1
            continue
            
        # 파일명에서 의결번호 추출
        filename = pdf_file.name
        if "제2025-" in filename:
            try:
                decision_num = filename.split("제2025-")[1].split("호")[0]
                decision_id = int(decision_num)
                if decision_id not in processed_ids:
                    pdf_files.append(pdf_file)
                else:
                    already_processed += 1
            except:
                # 번호 추출 실패 시에도 처리 시도
                pdf_files.append(pdf_file)
    
    logger.info(f"처리 상황: 전체 {len(all_pdf_files)}개, V2 완료 {already_processed}개, 건너뜀 {skipped_count}개")
    logger.info(f"처리할 파일: {len(pdf_files)}개")
    
    if not pdf_files:
        logger.info("처리할 새로운 PDF 파일이 없습니다.")
        return
    
    # 파일 정렬 (번호 순)
    pdf_files.sort(key=lambda x: int(x.name.split("제2025-")[1].split("호")[0]) if "제2025-" in x.name else 999)
    
    # 20개만 선택
    pdf_files = pdf_files[:20]
    logger.info(f"20개 파일 처리 예정")
    
    # 처리할 파일 목록 출력
    logger.info("\n처리할 파일 목록:")
    for i, pdf_file in enumerate(pdf_files, 1):
        logger.info(f"  {i}. {pdf_file.name}")
    
    # 전체 통계
    total_success = 0
    total_fail = 0
    failed_files = []
    
    # 각 파일 처리
    for idx, pdf_path in enumerate(pdf_files, 1):
        progress = idx / len(pdf_files) * 100
        logger.info(f"\n[{idx}/{len(pdf_files)} ({progress:.1f}%)] {pdf_path.name}")
        
        success, message = await process_single_file(pdf_path)
        
        if success:
            total_success += 1
            logger.info(f"✅ {message}")
        else:
            total_fail += 1
            failed_files.append((pdf_path.name, message))
            logger.error(f"❌ {message}")
        
        # 매 3개 처리 후 잠시 대기 (API 레이트 리밋)
        if idx % 3 == 0 and idx < len(pdf_files):
            logger.info("3개 처리 완료, 5초 대기...")
            await asyncio.sleep(5)
    
    # 최종 결과 요약
    logger.info(f"\n{'='*60}")
    logger.info("처리 요약")
    logger.info(f"{'='*60}")
    logger.info(f"처리 시도: {len(pdf_files)}개")
    logger.info(f"성공: {total_success}개")
    logger.info(f"실패: {total_fail}개")
    
    if failed_files:
        logger.info(f"\n실패한 파일 목록:")
        for filename, reason in failed_files:
            logger.info(f"  - {filename}: {reason}")
    
    # 최종 데이터베이스 상태
    db = SessionLocal()
    try:
        total_v2_decisions = db.query(DecisionV2).filter(DecisionV2.decision_year == 2025).count()
        logger.info(f"\nV2 시스템의 2025년 총 의결서: {total_v2_decisions}개")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())