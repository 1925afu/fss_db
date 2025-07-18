#!/usr/bin/env python3
"""
PDF 처리 스크립트
"""

import asyncio
import sys
import argparse
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.pdf_processor import PDFProcessor
from app.core.database import SessionLocal
from app.core.config import settings
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_processing.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description='PDF 처리 스크립트')
    parser.add_argument('--pdf-dir', type=str, help='PDF 디렉토리', default=settings.PROCESSED_PDF_DIR)
    parser.add_argument('--single-file', type=str, help='단일 파일 처리', default=None)
    parser.add_argument('--stats', action='store_true', help='처리 통계 출력')
    parser.add_argument('--fsc-only', action='store_true', default=True, help='금융위 의결서 형식만 처리 (기본값)')
    parser.add_argument('--processing-mode', type=str, choices=['rule-based', 'hybrid', 'ai-only'], 
                        default='hybrid', help='처리 모드 선택 (기본값: hybrid)')
    
    args = parser.parse_args()
    
    try:
        # 데이터베이스 세션 생성
        db = SessionLocal()
        
        # PDF 프로세서 초기화 (2단계 파이프라인 사용)
        processor = PDFProcessor(db, use_2_step_pipeline=True, processing_mode=args.processing_mode)
        
        if args.stats:
            # 처리 통계 출력
            stats = processor.get_processing_stats(fsc_only=args.fsc_only)
            logger.info("=== 처리 통계 ===")
            logger.info(f"전체 PDF 파일 수: {stats['total_pdf_files']}")
            if args.fsc_only:
                logger.info(f"처리 대상 PDF 파일 수 (금융위 의결서 형식): {stats['target_pdf_files']}")
            else:
                logger.info(f"처리 대상 PDF 파일 수 (의결*. 형식): {stats['target_pdf_files']}")
            logger.info(f"처리된 의결서 수: {stats['total_decisions']}")
            logger.info(f"처리된 조치 수: {stats['total_actions']}")
            logger.info(f"처리된 법률 수: {stats['total_laws']}")
            logger.info(f"처리율: {stats['processing_rate']}")
            
        elif args.single_file:
            # 단일 파일 처리
            logger.info(f"단일 파일 처리 시작 ({args.processing_mode} 모드): {args.single_file}")
            result = await processor.process_single_pdf(args.single_file, processing_mode=args.processing_mode)
            
            if result['success']:
                logger.info("파일 처리 완료!")
                logger.info(f"의결서 ID: {result['db_result']['decision_id']}")
                logger.info(f"조치 수: {len(result['db_result']['actions_saved'])}")
                logger.info(f"법률 수: {result['db_result']['laws_saved']}")
            else:
                logger.error(f"파일 처리 실패: {result['error']}")
                
        else:
            # 모든 PDF 파일 처리
            if args.fsc_only:
                logger.info(f"금융위 의결서 형식 PDF 파일 처리 시작 ({args.processing_mode} 모드)")
            else:
                logger.info(f"모든 의결 PDF 파일 처리 시작 ({args.processing_mode} 모드)")
            results = await processor.process_all_pdfs(fsc_only=args.fsc_only)
            
            # 결과 요약
            successful = sum(1 for r in results if r['success'])
            failed = len(results) - successful
            
            logger.info("=== 처리 결과 ===")
            logger.info(f"총 파일 수: {len(results)}")
            logger.info(f"성공: {successful}")
            logger.info(f"실패: {failed}")
            
            # 실패한 파일 목록
            if failed > 0:
                logger.info("실패한 파일 목록:")
                for result in results:
                    if not result['success']:
                        logger.info(f"  - {result['pdf_path']}: {result['error']}")
        
        logger.info("PDF 처리 완료!")
        
    except Exception as e:
        logger.error(f"PDF 처리 실패: {str(e)}")
        sys.exit(1)
    
    finally:
        if 'db' in locals():
            db.close()


if __name__ == '__main__':
    asyncio.run(main())