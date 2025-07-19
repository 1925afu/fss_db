#!/usr/bin/env python3
"""
2025년 의결서만 추출하는 스크립트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from app.services.pdf_processor import PDFProcessor
from app.core.database import SessionLocal
import logging
import re

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
        
        # 2025년 PDF 파일만 필터링
        all_pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf') and f.startswith('금융위 의결서')]
        pdf_files_2025 = []
        
        for pdf_file in all_pdf_files:
            # 파일명에서 연도 추출
            year_match = re.search(r'제(\d{4})-\d+호', pdf_file)
            if year_match and year_match.group(1) == '2025':
                pdf_files_2025.append(pdf_file)
        
        logger.info(f"전체 PDF 파일 수: {len(all_pdf_files)}")
        logger.info(f"2025년 PDF 파일 수: {len(pdf_files_2025)}")
        
        if not pdf_files_2025:
            logger.warning("2025년 PDF 파일이 없습니다.")
            return
        
        # 각 PDF 처리
        success_count = 0
        error_count = 0
        
        # 주요 의결서 먼저 처리 (66호, 69호)
        priority_files = []
        other_files = []
        
        for pdf_file in pdf_files_2025:
            if '2025-66호' in pdf_file or '2025-69호' in pdf_file:
                priority_files.append(pdf_file)
            else:
                other_files.append(pdf_file)
        
        # 정렬하여 처리 순서 결정
        pdf_files_2025 = sorted(priority_files) + sorted(other_files)
        
        for i, pdf_file in enumerate(pdf_files_2025, 1):
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"처리 중 ({i}/{len(pdf_files_2025)}): {pdf_file}")
                logger.info(f"{'='*60}")
                
                # 각 파일마다 새로운 세션 생성
                db = SessionLocal()
                processor = PDFProcessor(db)
                
                pdf_path = os.path.join(pdf_dir, pdf_file)
                result = await processor.process_single_pdf(pdf_path)
                
                if result:
                    success_count += 1
                    logger.info(f"✓ 성공적으로 처리됨: {pdf_file}")
                    
                    # 결과 요약 출력
                    if 'actions' in result:
                        logger.info(f"  - 조치 수: {len(result['actions'])}")
                        for action in result['actions']:
                            logger.info(f"    · {action.get('entity_name', 'Unknown')}: {action.get('action_type', 'Unknown')} - {action.get('fine_amount', 0):,}원")
                else:
                    error_count += 1
                    logger.error(f"✗ 처리 실패: {pdf_file}")
                    
            except Exception as e:
                error_count += 1
                logger.error(f"✗ 오류 발생 {pdf_file}: {str(e)}")
                continue
            finally:
                # 세션 닫기
                db.close()
        
        # 최종 결과
        logger.info(f"\n{'='*60}")
        logger.info("2025년 PDF 추출 프로세스 완료")
        logger.info(f"총 파일: {len(pdf_files_2025)}")
        logger.info(f"성공: {success_count}")
        logger.info(f"실패: {error_count}")
        logger.info(f"{'='*60}")
        
    except Exception as e:
        logger.error(f"치명적 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())