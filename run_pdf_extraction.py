#!/usr/bin/env python3
"""
PDF 추출 프로세스를 실행하는 스크립트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from app.services.pdf_processor import PDFProcessor
from app.core.database import SessionLocal
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """메인 함수"""
    try:
        # 데이터베이스 세션 생성
        db = SessionLocal()
        
        # PDF 처리기 초기화
        processor = PDFProcessor(db)
        
        # PDF 디렉토리 확인
        pdf_dir = "./data/processed_pdf"
        if not os.path.exists(pdf_dir):
            logger.error(f"PDF 디렉토리가 존재하지 않습니다: {pdf_dir}")
            return
        
        # PDF 파일 목록
        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf') and f.startswith('금융위 의결서')]
        logger.info(f"처리할 PDF 파일 수: {len(pdf_files)}")
        
        if not pdf_files:
            logger.warning("처리할 PDF 파일이 없습니다.")
            return
        
        # 각 PDF 처리
        success_count = 0
        error_count = 0
        
        for i, pdf_file in enumerate(pdf_files, 1):
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"처리 중 ({i}/{len(pdf_files)}): {pdf_file}")
                logger.info(f"{'='*60}")
                
                pdf_path = os.path.join(pdf_dir, pdf_file)
                result = await processor.process_single_pdf(pdf_path)
                
                if result:
                    success_count += 1
                    logger.info(f"✓ 성공적으로 처리됨: {pdf_file}")
                else:
                    error_count += 1
                    logger.error(f"✗ 처리 실패: {pdf_file}")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"✗ 오류 발생 {pdf_file}: {str(e)}")
                continue
        
        # 최종 결과
        logger.info(f"\n{'='*60}")
        logger.info("PDF 추출 프로세스 완료")
        logger.info(f"총 파일: {len(pdf_files)}")
        logger.info(f"성공: {success_count}")
        logger.info(f"실패: {error_count}")
        logger.info(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"치명적 오류 발생: {str(e)}")
        raise
    finally:
        # 데이터베이스 연결 종료
        db.close()

if __name__ == "__main__":
    asyncio.run(main())