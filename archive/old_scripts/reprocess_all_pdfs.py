#!/usr/bin/env python3
"""
2025년 의결서 전체 재처리 스크립트
- 개선된 복수 조치 감지 로직 적용
- 하이브리드 방식으로 처리
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.pdf_processor import PDFProcessor
from app.models.fsc_models import Decision, Action, Law, ActionLawMap
from app.core.config import settings
from app.core.database import Base

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'reprocess_all_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 데이터베이스 설정
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def reprocess_all_pdfs():
    """모든 PDF 파일 재처리"""
    
    db = SessionLocal()
    pdf_processor = PDFProcessor(db, use_2_step_pipeline=True, processing_mode='rule-based')
    
    try:
        logger.info("=" * 80)
        logger.info("2025년 의결서 전체 재처리 시작")
        logger.info("=" * 80)
        
        # PDF 디렉토리 확인
        pdf_dir = settings.PROCESSED_PDF_DIR
        if not os.path.exists(pdf_dir):
            logger.error(f"PDF 디렉토리가 존재하지 않습니다: {pdf_dir}")
            return
        
        # 처리할 PDF 파일 목록
        all_files = os.listdir(pdf_dir)
        fsc_files = [f for f in all_files if f.endswith('.pdf') and '금융위 의결서' in f]
        
        logger.info(f"전체 PDF 파일 수: {len(all_files)}")
        logger.info(f"처리할 금융위 의결서 파일 수: {len(fsc_files)}")
        
        # 처리 결과 통계
        success_count = 0
        fail_count = 0
        multiple_sanctions_count = 0
        error_files = []
        
        # 파일별 처리
        for idx, filename in enumerate(fsc_files, 1):
            pdf_path = os.path.join(pdf_dir, filename)
            logger.info(f"\n[{idx}/{len(fsc_files)}] 처리 중: {filename}")
            
            try:
                # PDF 처리 (Rule-based 모드로 빠른 처리)
                result = await pdf_processor.process_single_pdf(pdf_path, processing_mode='rule-based')
                
                if result['success']:
                    success_count += 1
                    
                    # 복수 조치 여부 확인
                    if result.get('extracted_data', {}).get('actions'):
                        action = result['extracted_data']['actions'][0]
                        target_details = action.get('target_details', {})
                        if target_details.get('type') == 'multiple_sanctions':
                            multiple_sanctions_count += 1
                            logger.info(f"  → 복수 조치 감지: {target_details.get('total_count')}개 대상, 총 {target_details.get('total_fine'):,}원")
                else:
                    fail_count += 1
                    error_files.append((filename, result.get('error', 'Unknown error')))
                    logger.error(f"  → 처리 실패: {result.get('error')}")
                    
            except Exception as e:
                fail_count += 1
                error_files.append((filename, str(e)))
                logger.error(f"  → 예외 발생: {str(e)}")
        
        # 처리 완료 후 통계
        logger.info("\n" + "=" * 80)
        logger.info("처리 완료 통계")
        logger.info("=" * 80)
        logger.info(f"전체 파일: {len(fsc_files)}개")
        logger.info(f"성공: {success_count}개")
        logger.info(f"실패: {fail_count}개")
        logger.info(f"복수 조치 의결서: {multiple_sanctions_count}개")
        
        # DB 통계
        total_decisions = db.query(Decision).count()
        total_actions = db.query(Action).count()
        total_laws = db.query(Law).count()
        total_mappings = db.query(ActionLawMap).count()
        
        logger.info(f"\nDB 저장 통계:")
        logger.info(f"의결서: {total_decisions}개")
        logger.info(f"조치: {total_actions}개")
        logger.info(f"법률: {total_laws}개")
        logger.info(f"법률매핑: {total_mappings}개")
        
        # 실패 파일 목록
        if error_files:
            logger.error(f"\n실패한 파일 목록:")
            for filename, error in error_files:
                logger.error(f"  - {filename}: {error}")
        
        # 날짜 업데이트 처리
        logger.info("\n날짜 정보 업데이트 시작...")
        from update_decision_dates import update_all_decision_dates
        update_all_decision_dates(db)
        
    except Exception as e:
        logger.error(f"전체 처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        logger.info("\n재처리 완료")

if __name__ == "__main__":
    asyncio.run(reprocess_all_pdfs())