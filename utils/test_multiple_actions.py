#!/usr/bin/env python3
"""
2025-45호 문서로 복수 조치 처리 테스트
"""

import os
import sys
import asyncio
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.pdf_processor import PDFProcessor
from app.services.rule_based_extractor import RuleBasedExtractor
from app.models.fsc_models import Decision, Action
from app.core.config import settings
from app.core.database import Base

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 데이터베이스 설정
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def test_multiple_actions():
    """2025-45호 문서로 복수 조치 처리 테스트"""
    
    db = SessionLocal()
    pdf_processor = PDFProcessor(db, use_2_step_pipeline=True, processing_mode='hybrid')
    rule_based_extractor = RuleBasedExtractor()
    
    # 2025-45호 PDF 파일 경로
    pdf_path = os.path.join(settings.PROCESSED_PDF_DIR, "금융위 의결서(제2025-45호)_㈜OOO의 사업보고서 및 연결감사보고서 등에 대한 조사·감리 결과 조치안(공개용).pdf")
    
    if not os.path.exists(pdf_path):
        logger.error(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return
    
    logger.info("=" * 80)
    logger.info("2025-45호 문서 복수 조치 처리 테스트 시작")
    logger.info("=" * 80)
    
    try:
        # 1. PDF 텍스트 추출
        pdf_text = pdf_processor.extract_text_from_pdf(pdf_path)
        if not pdf_text:
            logger.error("PDF 텍스트 추출 실패")
            return
        
        logger.info(f"PDF 텍스트 추출 완료: {len(pdf_text)} 문자")
        
        # 추출된 텍스트 일부 확인
        logger.info("추출된 텍스트 첫 1000자:")
        logger.info(pdf_text[:1000])
        logger.info("\n텍스트에서 '과징금' 검색:")
        if '과징금' in pdf_text:
            logger.info("'과징금' 발견")
            # 과징금 주변 텍스트 확인
            idx = pdf_text.find('과징금')
            logger.info(f"과징금 주변 텍스트: {pdf_text[max(0, idx-50):idx+50]}")
        else:
            logger.info("'과징금' 미발견")
        
        # 2. 복수 조치 감지 테스트
        has_multiple = rule_based_extractor.detect_multiple_actions(pdf_text)
        logger.info(f"복수 조치 감지 결과: {has_multiple}")
        
        # 3. Rule-based 복수 조치 추출 테스트
        filename = os.path.basename(pdf_path)
        actions = rule_based_extractor.extract_actions_and_violations(pdf_text, filename)
        
        logger.info(f"\nRule-based 추출 결과:")
        logger.info(f"추출된 조치 수: {len(actions)}")
        for i, action in enumerate(actions, 1):
            logger.info(f"\n조치 {i}:")
            logger.info(f"  - 대상자: {action.get('entity_name')}")
            logger.info(f"  - 업권: {action.get('industry_sector')}")
            logger.info(f"  - 조치 유형: {action.get('action_type')}")
            logger.info(f"  - 금액: {action.get('fine_amount'):,}원" if action.get('fine_amount') else "  - 금액: 없음")
        
        # 4. 전체 처리 파이프라인 테스트
        logger.info("\n" + "=" * 80)
        logger.info("전체 하이브리드 처리 파이프라인 테스트")
        logger.info("=" * 80)
        
        # 기존 데이터 삭제 (테스트를 위해)
        existing_decision = db.query(Decision).filter(
            Decision.decision_year == 2025,
            Decision.decision_id == 45
        ).first()
        
        if existing_decision:
            # 관련 actions 삭제
            db.query(Action).filter(
                Action.decision_year == 2025,
                Action.decision_id == 45
            ).delete()
            # decision 삭제
            db.delete(existing_decision)
            db.commit()
            logger.info("기존 2025-45호 데이터 삭제 완료")
        
        # 하이브리드 처리
        result = await pdf_processor.process_single_pdf(pdf_path, processing_mode='hybrid')
        
        if result['success']:
            logger.info(f"\n처리 성공!")
            logger.info(f"처리 모드: {result.get('processing_mode')}")
            
            # DB에서 저장된 데이터 확인
            decision = db.query(Decision).filter(
                Decision.decision_year == 2025,
                Decision.decision_id == 45
            ).first()
            
            if decision:
                actions_in_db = db.query(Action).filter(
                    Action.decision_year == 2025,
                    Action.decision_id == 45
                ).all()
                
                logger.info(f"\nDB 저장 결과:")
                logger.info(f"의결서 제목: {decision.title}")
                logger.info(f"저장된 조치 수: {len(actions_in_db)}")
                
                total_fine = 0
                for i, action in enumerate(actions_in_db, 1):
                    logger.info(f"\n조치 {i} (DB):")
                    logger.info(f"  - action_id: {action.action_id}")
                    logger.info(f"  - 대상자: {action.entity_name}")
                    logger.info(f"  - 업권: {action.industry_sector}")
                    logger.info(f"  - 조치 유형: {action.action_type}")
                    logger.info(f"  - 금액: {action.fine_amount:,}원" if action.fine_amount else "  - 금액: 없음")
                    if action.fine_amount:
                        total_fine += action.fine_amount
                
                logger.info(f"\n총 과징금 합계: {total_fine:,}원")
                logger.info(f"예상 합계 (5,451,900,000원)와의 차이: {abs(total_fine - 5451900000):,}원")
        else:
            logger.error(f"처리 실패: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        logger.info("\n테스트 완료")

if __name__ == "__main__":
    asyncio.run(test_multiple_actions())