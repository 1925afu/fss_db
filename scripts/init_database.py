#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import engine, Base
from app.models.fsc_models import Decision, Action, Law, ActionLawMap
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_database():
    """데이터베이스 테이블 생성"""
    try:
        logger.info("데이터베이스 테이블 초기화 시작...")
        
        # 기존 테이블 삭제
        logger.info("기존 테이블 삭제 중...")
        Base.metadata.drop_all(bind=engine)
        
        # 모든 테이블 생성
        logger.info("새로운 테이블 생성 중...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("데이터베이스 테이블 생성 완료!")
        logger.info("생성된 테이블:")
        logger.info("- decisions")
        logger.info("- actions")
        logger.info("- laws")
        logger.info("- action_law_maps")
        
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise

if __name__ == "__main__":
    init_database()