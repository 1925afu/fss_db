"""
V2 파이프라인 10개 파일 배치 테스트
"""
import asyncio
import logging
import os
from datetime import datetime
from app.services.pdf_processor_v2 import PDFProcessorV2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_batch_10():
    """10개 파일 배치 처리 테스트"""
    try:
        processor = PDFProcessorV2()
        
        # 2025년 PDF 파일들 중 10개만 테스트
        test_dir = "data/processed_pdf/2025"
        all_files = [f for f in os.listdir(test_dir) if f.endswith('.pdf') and '금융위 의결서' in f]
        test_files = [os.path.join(test_dir, f) for f in sorted(all_files)[:10]]  # 처음 10개만
        
        logger.info(f"=== V2 파이프라인 10개 파일 배치 테스트 ===")
        logger.info(f"테스트 파일 수: {len(test_files)}")
        
        # 배치 처리
        start_time = datetime.now()
        results = await processor.process_batch(test_files, batch_size=5)
        end_time = datetime.now()
        
        # 결과 요약
        logger.info(f"\n=== 배치 처리 결과 ===")
        logger.info(f"전체: {results['total']}")
        logger.info(f"성공: {len(results['success'])}") 
        logger.info(f"실패: {len(results['failed'])}")
        logger.info(f"처리 시간: {(end_time - start_time).total_seconds():.2f}초")
        logger.info(f"평균 처리 시간: {(end_time - start_time).total_seconds() / results['total']:.2f}초/파일")
        
        # 실패 분석
        if results['failed']:
            logger.warning(f"\n실패한 파일들 ({len(results['failed'])}개):")
            for failed in results['failed']:
                logger.warning(f"  - {os.path.basename(failed['pdf_path'])}: {failed['error']}")
        
        # 통계
        stats = processor.get_statistics()
        logger.info(f"\n=== 최종 DB 통계 ===")
        logger.info(f"총 의결서: {stats['total_decisions']}")
        logger.info(f"총 조치: {stats['total_actions']}")
        logger.info(f"총 법률: {stats['total_laws']}")
        logger.info(f"총 법률매핑: {stats['total_law_mappings']}")
        
        if stats.get('by_year'):
            logger.info("\n연도별 의결서:")
            for year, count in sorted(stats['by_year'].items()):
                logger.info(f"  - {year}년: {count}개")
        
        if stats.get('by_category'):
            logger.info("\n카테고리별 의결서:")
            for category, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  - {category}: {count}개")
        
    except Exception as e:
        logger.error(f"배치 테스트 오류: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_batch_10())