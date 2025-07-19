#!/usr/bin/env python3
"""
배치로 데이터베이스의 날짜를 업데이트하는 스크립트
PDF 처리 후 별도로 실행하여 날짜를 보정할 수 있습니다.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.update_decision_dates import update_database_dates
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """메인 함수"""
    db_path = "./fss_db.sqlite"
    processed_pdf_dir = "./data/processed_pdf"
    
    logger.info("=" * 60)
    logger.info("의결서 날짜 업데이트 배치 작업 시작")
    logger.info("=" * 60)
    
    # 날짜 업데이트 실행
    update_database_dates(db_path, processed_pdf_dir)
    
    logger.info("=" * 60)
    logger.info("의결서 날짜 업데이트 배치 작업 완료")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()