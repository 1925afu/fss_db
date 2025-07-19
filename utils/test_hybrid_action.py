#!/usr/bin/env python3
"""
하이브리드 방식 복수 조치 처리 테스트
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
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 데이터베이스 설정
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def test_hybrid_approach():
    """하이브리드 방식 테스트"""
    
    db = SessionLocal()
    pdf_processor = PDFProcessor(db, use_2_step_pipeline=True, processing_mode='rule-based')
    rule_based_extractor = RuleBasedExtractor()
    
    # PDF 파일 경로 (명령줄 인자로 받거나 기본값 사용)
    if len(sys.argv) > 1:
        pdf_filename = sys.argv[1]
    else:
        pdf_filename = "금융위 의결서(제2025-119호)_㈜OO의 사업보고서 및 연결감사보고서 등에 대한 조사·감리결과 조치안(공개용).pdf"
    
    pdf_path = os.path.join(settings.PROCESSED_PDF_DIR, pdf_filename)
    
    if not os.path.exists(pdf_path):
        logger.error(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        return
    
    logger.info("=" * 80)
    logger.info("하이브리드 방식 복수 조치 처리 테스트")
    logger.info("=" * 80)
    
    try:
        # 1. PDF 텍스트 추출
        pdf_text = pdf_processor.extract_text_from_pdf(pdf_path)
        filename = os.path.basename(pdf_path)
        
        # 2. Rule-based 추출 및 통합
        result = rule_based_extractor.extract_full_document_structure(pdf_text, filename)
        
        logger.info(f"\n추출 결과:")
        logger.info(f"의결서 정보: {result['decision']['title']}")
        logger.info(f"조치 수: {len(result['actions'])}")
        
        # 3. 통합된 action 정보 확인
        if result['actions']:
            action = result['actions'][0]
            logger.info(f"\n통합 Action 정보:")
            logger.info(f"  - entity_name: {action.get('entity_name')}")
            logger.info(f"  - industry_sector: {action.get('industry_sector')}")
            logger.info(f"  - action_type: {action.get('action_type')}")
            logger.info(f"  - fine_amount: {action.get('fine_amount'):,}원")
            
            # target_details 확인
            target_details = action.get('target_details', {})
            if target_details and isinstance(target_details, dict) and target_details.get('type') == 'multiple_sanctions':
                logger.info(f"\n  target_details:")
                logger.info(f"    - type: {target_details.get('type')}")
                logger.info(f"    - total_count: {target_details.get('total_count')}")
                logger.info(f"    - primary_entity: {target_details.get('primary_entity')}")
                logger.info(f"    - total_fine: {target_details.get('total_fine'):,}원")
                
                logger.info(f"\n    개별 대상자:")
                for i, target in enumerate(target_details.get('targets', []), 1):
                    logger.info(f"    {i}. {target.get('entity_name')}")
                    logger.info(f"       - entity_type: {target.get('entity_type')}")
                    logger.info(f"       - fine_amount: {target.get('fine_amount'):,}원")
                    if target.get('position'):
                        logger.info(f"       - position: {target.get('position')}")
                    if target.get('industry_sector'):
                        logger.info(f"       - industry_sector: {target.get('industry_sector')}")
            else:
                logger.info(f"\n  target_details: 단일 조치 (복수 조치 아님)")
        
        # 4. DB 저장 테스트
        logger.info("\n" + "=" * 80)
        logger.info("DB 저장 테스트")
        logger.info("=" * 80)
        
        # 의결번호 추출
        import re
        decision_match = re.search(r'제(\d{4})-(\d+)호', pdf_filename)
        if decision_match:
            year = int(decision_match.group(1))
            decision_id = int(decision_match.group(2))
        else:
            logger.error("파일명에서 의결번호를 추출할 수 없습니다")
            return
            
        # 기존 데이터 삭제
        existing_decision = db.query(Decision).filter(
            Decision.decision_year == year,
            Decision.decision_id == decision_id
        ).first()
        
        if existing_decision:
            db.query(Action).filter(
                Action.decision_year == year,
                Action.decision_id == decision_id
            ).delete()
            db.delete(existing_decision)
            db.commit()
            logger.info(f"기존 {year}-{decision_id}호 데이터 삭제 완료")
        
        # PDF 처리 (Rule-based only로 빠른 테스트)
        process_result = await pdf_processor.process_single_pdf(pdf_path, processing_mode='rule-based')
        
        if process_result['success']:
            logger.info(f"\n처리 성공!")
            
            # DB에서 저장된 데이터 확인
            decision = db.query(Decision).filter(
                Decision.decision_year == year,
                Decision.decision_id == decision_id
            ).first()
            
            if decision:
                actions_in_db = db.query(Action).filter(
                    Action.decision_year == year,
                    Action.decision_id == decision_id
                ).all()
                
                logger.info(f"\nDB 저장 결과:")
                logger.info(f"의결서 제목: {decision.title}")
                logger.info(f"저장된 조치 수: {len(actions_in_db)}")
                
                if actions_in_db:
                    action = actions_in_db[0]
                    logger.info(f"\n저장된 Action:")
                    logger.info(f"  - action_id: {action.action_id}")
                    logger.info(f"  - entity_name: {action.entity_name}")
                    logger.info(f"  - industry_sector: {action.industry_sector}")
                    logger.info(f"  - action_type: {action.action_type}")
                    logger.info(f"  - fine_amount: {action.fine_amount:,}원")
                    
                    # JSON 필드 확인
                    if action.target_details:
                        logger.info(f"\n  target_details (JSON):")
                        logger.info(json.dumps(action.target_details, ensure_ascii=False, indent=2))
        else:
            logger.error(f"처리 실패: {process_result.get('error')}")
            
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        logger.info("\n테스트 완료")

if __name__ == "__main__":
    asyncio.run(test_hybrid_approach())