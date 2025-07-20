"""
V2 파이프라인 단일 파일 테스트
"""
import asyncio
import logging
import os
from app.services.pdf_processor_v2 import PDFProcessorV2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_single():
    """단일 파일 테스트"""
    try:
        processor = PDFProcessorV2()
        
        # 2025-60 파일 테스트
        test_file = "data/processed_pdf/2025/금융위 의결서(제2025-60호)_도미넌트자산운용㈜에 대한 수시검사 결과 조치안(공개용).pdf"
        
        if not os.path.exists(test_file):
            logger.error(f"테스트 파일이 없습니다: {test_file}")
            return
        
        logger.info(f"테스트 시작: {test_file}")
        result = await processor.process_single_pdf(test_file)
        
        if result['success']:
            logger.info("✅ 성공!")
            db_result = result.get('db_result', {})
            logger.info(f"의결서: {db_result.get('decision_year')}-{db_result.get('decision_id')}")
            logger.info(f"조치 수: {len(db_result.get('actions_saved', []))}")
            
            # 최종 통계
            stats = processor.get_statistics()
            logger.info(f"\n=== 최종 DB 통계 ===")
            logger.info(f"V2 의결서: {stats['total_decisions']}개")
            logger.info(f"V2 조치: {stats['total_actions']}개")
            logger.info(f"V2 법률: {stats['total_laws']}개")
            logger.info(f"V2 법률매핑: {stats['total_law_mappings']}개")
        else:
            logger.error(f"❌ 실패: {result['error']}")
            
    except Exception as e:
        logger.error(f"테스트 오류: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_single())