#!/usr/bin/env python3
"""
FSC 의결서 크롤러 스크립트
"""

import asyncio
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.fsc_crawler import FSCCrawler
from app.core.config import settings
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='FSC 의결서 크롤러')
    parser.add_argument('--start-date', type=str, help='시작 날짜 (YYYY-MM-DD)', required=True)
    parser.add_argument('--end-date', type=str, help='종료 날짜 (YYYY-MM-DD)', required=True)
    parser.add_argument('--output-dir', type=str, help='출력 디렉토리', default=settings.RAW_ZIP_DIR)
    
    args = parser.parse_args()
    
    try:
        # 날짜 파싱
        start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
        
        logger.info(f"크롤링 시작: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        
        # 크롤러 초기화
        crawler = FSCCrawler()
        
        # 크롤링 실행
        results = crawler.crawl_decisions(start_date, end_date)
        
        # 결과 출력
        logger.info("=== 크롤링 결과 ===")
        logger.info(f"검색된 의결서 수: {len(results.get('decisions', []))}")
        logger.info(f"다운로드된 파일 수: {len(results.get('downloaded_files', []))}")
        logger.info(f"추출된 PDF 파일 수: {len(results.get('extracted_files', []))}")
        
        # 추출된 파일 목록 출력
        if results.get('extracted_files'):
            logger.info("추출된 PDF 파일 목록:")
            for file in results['extracted_files']:
                logger.info(f"  - {file}")
        
        logger.info("크롤링 완료!")
        
    except Exception as e:
        logger.error(f"크롤링 실패: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()