"""
V2 파이프라인 빠른 테스트
"""
import asyncio
import logging
import os
from app.services.pdf_processor_v2 import PDFProcessorV2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_single():
    """단일 파일 빠른 테스트"""
    try:
        processor = PDFProcessorV2()
        
        # 첫 번째 PDF 파일만 테스트
        test_file = "data/processed_pdf/2025/금융위 의결서(제2025-1호)_타이거자산운용투자일임㈜에 대한 수시검사 결과 조치안(공개용).pdf"
        
        if not os.path.exists(test_file):
            logger.error(f"테스트 파일이 없습니다: {test_file}")
            return
        
        logger.info(f"테스트 시작: {test_file}")
        result = await processor.process_single_pdf(test_file)
        
        if result['success']:
            logger.info("✅ 성공!")
            logger.info(f"의결서: {result['db_result']['decision_year']}-{result['db_result']['decision_id']}")
            logger.info(f"조치 수: {len(result['db_result']['actions_saved'])}")
        else:
            logger.error(f"❌ 실패: {result['error']}")
            
    except Exception as e:
        logger.error(f"테스트 오류: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_single())