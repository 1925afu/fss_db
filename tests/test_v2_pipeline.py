"""
V2 파이프라인 테스트 스크립트
샘플 PDF로 새로운 Structured Output 기반 시스템 테스트
"""
import asyncio
import logging
import os
import sys
from datetime import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.pdf_processor_v2 import PDFProcessorV2

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'test_v2_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def test_single_pdf():
    """단일 PDF 파일 테스트"""
    logger.info("=== V2 파이프라인 단일 PDF 테스트 시작 ===")
    
    # 프로세서 초기화
    processor = PDFProcessorV2()
    
    # 테스트할 PDF 파일 선택 (2025년 첫 번째 파일)
    test_dir = "data/processed_pdf/2025"
    pdf_files = [f for f in os.listdir(test_dir) if f.endswith('.pdf') and '금융위 의결서' in f]
    
    if not pdf_files:
        logger.error("테스트할 PDF 파일이 없습니다.")
        return
    
    # 첫 번째 파일로 테스트
    test_file = os.path.join(test_dir, sorted(pdf_files)[0])
    logger.info(f"테스트 파일: {test_file}")
    
    # 처리 실행
    result = await processor.process_single_pdf(test_file)
    
    # 결과 출력
    if result['success']:
        logger.info("✅ 처리 성공!")
        logger.info(f"의결서: {result['db_result']['decision_year']}-{result['db_result']['decision_id']}")
        logger.info(f"조치 수: {len(result['db_result']['actions_saved'])}")
        
        # 상세 정보 출력
        decision_data = result['decision_data']
        logger.info(f"제목: {decision_data['title']}")
        logger.info(f"카테고리: {decision_data.get('category_1')} / {decision_data.get('category_2')}")
        
        for i, action in enumerate(decision_data['actions'], 1):
            logger.info(f"\n조치 {i}:")
            logger.info(f"  - 대상: {action['entity_name']}")
            logger.info(f"  - 유형: {action['action_type']}")
            if action.get('fine_amount'):
                logger.info(f"  - 금액: {action['fine_amount']:,}원")
            logger.info(f"  - 위반요약: {action['violation_summary'][:100]}...")
            logger.info(f"  - 관련법률: {len(action['action_law_map'])}개")
    else:
        logger.error(f"❌ 처리 실패: {result['error']}")
    
    # 통계 출력
    stats = processor.get_statistics()
    logger.info(f"\n=== 현재 DB 통계 ===")
    logger.info(f"총 의결서: {stats['total_decisions']}")
    logger.info(f"총 조치: {stats['total_actions']}")
    logger.info(f"총 법률: {stats['total_laws']}")
    logger.info(f"총 법률매핑: {stats['total_law_mappings']}")


async def test_batch_processing():
    """배치 처리 테스트"""
    logger.info("\n=== V2 파이프라인 배치 처리 테스트 시작 ===")
    
    # 프로세서 초기화
    processor = PDFProcessorV2()
    
    # 테스트할 PDF 파일들 (10개)
    test_dir = "data/processed_pdf/2025"
    all_files = [f for f in os.listdir(test_dir) if f.endswith('.pdf') and '금융위 의결서' in f]
    test_files = [os.path.join(test_dir, f) for f in sorted(all_files)[:10]]
    
    logger.info(f"테스트 파일 수: {len(test_files)}")
    
    # 배치 처리 실행
    start_time = datetime.now()
    results = await processor.process_batch(test_files, batch_size=5)
    end_time = datetime.now()
    
    # 결과 요약
    logger.info(f"\n=== 배치 처리 결과 ===")
    logger.info(f"전체: {results['total']}")
    logger.info(f"성공: {len(results['success'])}")
    logger.info(f"실패: {len(results['failed'])}")
    logger.info(f"처리 시간: {(end_time - start_time).total_seconds():.2f}초")
    
    # 실패 사례 분석
    if results['failed']:
        logger.warning("\n실패한 파일들:")
        for failed in results['failed']:
            logger.warning(f"  - {os.path.basename(failed['pdf_path'])}: {failed['error']}")
    
    # 최종 통계
    stats = processor.get_statistics()
    logger.info(f"\n=== 최종 DB 통계 ===")
    logger.info(f"총 의결서: {stats['total_decisions']}")
    logger.info(f"총 조치: {stats['total_actions']}")
    logger.info(f"총 법률: {stats['total_laws']}")
    
    if stats.get('by_year'):
        logger.info("\n연도별 의결서:")
        for year, count in sorted(stats['by_year'].items()):
            logger.info(f"  - {year}년: {count}개")
    
    if stats.get('by_category'):
        logger.info("\n카테고리별 의결서:")
        for category, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  - {category}: {count}개")


async def compare_with_old_system():
    """기존 시스템과 비교"""
    logger.info("\n=== 기존 시스템과 비교 테스트 ===")
    
    # 두 DB의 통계 비교
    import sqlite3
    
    # 기존 DB
    old_conn = sqlite3.connect('fss_db.sqlite')
    old_cur = old_conn.cursor()
    
    old_stats = {
        'decisions': old_cur.execute("SELECT COUNT(*) FROM decisions").fetchone()[0],
        'actions': old_cur.execute("SELECT COUNT(*) FROM actions").fetchone()[0],
        'laws': old_cur.execute("SELECT COUNT(*) FROM laws").fetchone()[0],
    }
    old_conn.close()
    
    # 새 DB
    new_conn = sqlite3.connect('fss_db_v2.sqlite')
    new_cur = new_conn.cursor()
    
    new_stats = {
        'decisions': new_cur.execute("SELECT COUNT(*) FROM decisions_v2").fetchone()[0],
        'actions': new_cur.execute("SELECT COUNT(*) FROM actions_v2").fetchone()[0],
        'laws': new_cur.execute("SELECT COUNT(*) FROM laws_v2").fetchone()[0],
    }
    new_conn.close()
    
    logger.info("시스템 비교:")
    logger.info(f"의결서: 기존 {old_stats['decisions']} → 새 시스템 {new_stats['decisions']}")
    logger.info(f"조치: 기존 {old_stats['actions']} → 새 시스템 {new_stats['actions']}")
    logger.info(f"법률: 기존 {old_stats['laws']} → 새 시스템 {new_stats['laws']} (정규화됨)")


async def main():
    """메인 테스트 함수"""
    try:
        # 1. 단일 PDF 테스트
        await test_single_pdf()
        
        # 2. 배치 처리 테스트
        await test_batch_processing()
        
        # 3. 시스템 비교
        await compare_with_old_system()
        
        logger.info("\n=== 모든 테스트 완료 ===")
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())