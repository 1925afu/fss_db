#!/usr/bin/env python3
"""
크롤러 테스트 스크립트
"""

import sys
import os
from datetime import datetime, timedelta

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.fsc_crawler import FSCCrawler
from app.core.config import settings
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_crawler():
    """크롤러 기본 테스트"""
    logger.info("=== FSC 크롤러 테스트 시작 ===")
    
    # 크롤러 초기화
    crawler = FSCCrawler()
    
    # 테스트 기간 설정 (최근 1개월)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    logger.info(f"테스트 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    try:
        # 의결서 검색 테스트
        logger.info("1. 의결서 검색 테스트")
        decisions = crawler.search_decisions(start_date, end_date)
        logger.info(f"검색된 의결서 수: {len(decisions)}")
        
        if decisions:
            logger.info("첫 번째 의결서 정보:")
            first_decision = decisions[0]
            logger.info(f"  제목: {first_decision.get('title', 'N/A')}")
            logger.info(f"  날짜: {first_decision.get('date', 'N/A')}")
            logger.info(f"  번호: {first_decision.get('post_no', 'N/A')}")
            logger.info(f"  파일 수: {len(first_decision.get('files', []))}")
            
            # 파일 정보 출력
            for i, file_info in enumerate(first_decision.get('files', [])[:3]):  # 최대 3개만
                logger.info(f"  파일 {i+1}: {file_info.get('name', 'N/A')}")
        
        # 의결서 필터링 테스트
        logger.info("2. 의결서 필터링 테스트")
        filtered_decisions = [d for d in decisions if crawler._is_decision_document(d)]
        logger.info(f"필터링된 의결서 수: {len(filtered_decisions)}")
        
        if filtered_decisions:
            logger.info("필터링된 의결서 예시:")
            for i, decision in enumerate(filtered_decisions[:3]):  # 최대 3개만
                logger.info(f"  {i+1}. {decision.get('title', 'N/A')}")
        
        logger.info("=== 크롤러 테스트 완료 ===")
        
    except Exception as e:
        logger.error(f"크롤러 테스트 실패: {str(e)}")
        return False
    
    return True

if __name__ == '__main__':
    success = test_crawler()
    sys.exit(0 if success else 1)