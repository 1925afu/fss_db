#!/usr/bin/env python3
"""
PDF 처리 파이프라인 테스트 스크립트
"""

import sys
import os
sys.path.append('.')

from app.core.database import SessionLocal, init_db
from app.models.fsc_models import Decision, Action, Law, ActionLawMap
from datetime import date

# 데이터베이스 초기화
init_db()

# 테스트 데이터 생성
def create_test_data():
    """테스트용 데이터를 데이터베이스에 삽입"""
    db = SessionLocal()
    try:
        # 기존 데이터 정리
        db.query(ActionLawMap).delete()
        db.query(Action).delete()
        db.query(Decision).delete()
        db.query(Law).delete()
        
        # 법률 데이터 생성
        laws = [
            Law(law_name="은행법", law_short_name="은행법", law_category="은행"),
            Law(law_name="금융소비자 보호에 관한 법률", law_short_name="금융소비자보호법", law_category="금융일반")
        ]
        
        for law in laws:
            db.add(law)
        db.commit()
        
        # 의결서 데이터 생성
        decision = Decision(
            decision_year=2024,
            decision_id=1,
            decision_month=1,
            decision_day=15,
            agenda_no="제001호",
            title="A은행에 대한 제재조치",
            category_1="제재",
            category_2="기관",
            submitter="금융감독원",
            submission_date=date(2024, 1, 10),
            stated_purpose="A은행이 대출 심사 과정에서 부실한 내부통제 시스템을 운영하여 금융소비자 보호에 소홀한 바, 이에 대한 제재조치가 필요함.",
            full_text="A은행 내부통제 시스템 부실 운영으로 인한 제재",
            source_file="test_의결서_2024_001.txt"
        )
        
        db.add(decision)
        db.commit()
        
        # 조치 데이터 생성
        action = Action(
            decision_year=2024,
            decision_id=1,
            entity_name="A은행",
            industry_sector="은행",
            violation_details="대출 심사 과정에서 내부통제 절차 미준수, 금융소비자 보호 관련 규정 위반",
            action_type="과태료",
            fine_amount=500000000,  # 5억원
            effective_date=date(2024, 2, 1)
        )
        
        db.add(action)
        db.commit()
        
        # 법률 매핑 생성
        law_mappings = [
            ActionLawMap(
                action_id=action.action_id,
                law_id=laws[0].law_id,  # 은행법
                article_details="제37조",
                article_purpose="건전경영 의무"
            ),
            ActionLawMap(
                action_id=action.action_id,
                law_id=laws[1].law_id,  # 금융소비자보호법
                article_details="제19조",
                article_purpose="내부통제기준"
            )
        ]
        
        for mapping in law_mappings:
            db.add(mapping)
        db.commit()
        
        print("✅ 테스트 데이터 생성 완료")
        
        # 데이터 검증
        decisions_count = db.query(Decision).count()
        actions_count = db.query(Action).count()
        laws_count = db.query(Law).count()
        mappings_count = db.query(ActionLawMap).count()
        
        print(f"📊 생성된 데이터:")
        print(f"  - 의결서: {decisions_count}건")
        print(f"  - 조치: {actions_count}건")
        print(f"  - 법률: {laws_count}개")
        print(f"  - 매핑: {mappings_count}개")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        db.rollback()
    finally:
        db.close()

def test_data_integrity():
    """데이터 무결성 테스트"""
    db = SessionLocal()
    try:
        # 관계 데이터 조회 테스트
        decision = db.query(Decision).first()
        if decision:
            print(f"✅ 의결서 조회: {decision.title}")
            print(f"  - 결정일: {decision.decision_date}")
            print(f"  - 분류: {decision.category_1} > {decision.category_2}")
            
            # 관련 조치 조회
            actions = decision.actions
            print(f"  - 관련 조치: {len(actions)}건")
            
            for action in actions:
                print(f"    * {action.entity_name}: {action.action_type} ({action.fine_amount:,}원)")
                
                # 관련 법률 조회
                law_mappings = action.law_mappings
                print(f"      관련 법률: {len(law_mappings)}개")
                for mapping in law_mappings:
                    law = mapping.law
                    print(f"        - {law.law_short_name} {mapping.article_details}: {mapping.article_purpose}")
        
        print("✅ 데이터 무결성 테스트 통과")
        
    except Exception as e:
        print(f"❌ 데이터 무결성 테스트 실패: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    print("=== PDF 처리 파이프라인 테스트 ===")
    create_test_data()
    test_data_integrity()
    print("=== 테스트 완료 ===")