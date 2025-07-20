#!/usr/bin/env python3
"""
V2 시스템용 남은 4개 PDF 처리 스크립트
- Gemini 2.5 Flash 사용
- 이미 처리된 파일 제외
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
        logging.FileHandler(f'process_v2_remaining_4files_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 처리할 파일들 (이전에 실패한 4개)
TARGET_FILES = [
    "금융위 의결서(제2025-45호)_㈜OOO의 사업보고서 및 연결감사보고서 등에 대한 조사·감리 결과 조치안(공개용).pdf",
    "금융위 의결서(제2025-46호)_OOOOO㈜의 사업보고서 및 연결감사보고서 등에 대한 조사·감리 결과 조치안(공개용).pdf",
    "금융위 의결서(제2025-47호)_대한토지신탁㈜의 감사보고서 등에 대한 조사·감리결과 조치안(공개용).pdf",
    "금융위 의결서(제2025-48호)_공인회계사 OOO에 대한 징계의결안(공개용).pdf"
]

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
    
    # 처리할 파일 경로 확인
    pdf_files = []
    for filename in TARGET_FILES:
        pdf_path = pdf_dir / filename
        if pdf_path.exists():
            pdf_files.append(pdf_path)
        else:
            logger.warning(f"파일을 찾을 수 없습니다: {filename}")
    
    logger.info(f"처리할 파일: {len(pdf_files)}개")
    
    if not pdf_files:
        logger.info("처리할 PDF 파일이 없습니다.")
        return
    
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
        
        # 각 파일 처리 후 잠시 대기
        if idx < len(pdf_files):
            logger.info("다음 파일 처리 전 3초 대기...")
            await asyncio.sleep(3)
    
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