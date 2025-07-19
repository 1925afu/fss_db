#!/usr/bin/env python3
"""
Rule-based vs AI 정확도 분석 테스트
"""

import sys
import os
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.nl2sql_engine import NL2SQLEngine

async def test_accuracy():
    """정확도 분석 테스트"""
    
    print("=== Rule-based 정확도 분석 ===\n")
    
    db = SessionLocal()
    
    try:
        engine = NL2SQLEngine(db)
        
        # 정확도 테스트 케이스 (예상 결과 포함)
        test_cases = [
            {
                "query": "신한은행이 2025년에 받은 제재",
                "expected_entity": "신한은행",
                "expected_year": 2025,
                "should_contain": "신한"
            },
            {
                "query": "과테료 부과 사례들",  # 오타
                "expected_entity": None,  # 오타이므로 실패해야 함
                "should_fail": True
            },
            {
                "query": "1억원 이상 과징금",
                "expected_min_amount": 100000000,
                "expected_action": "과징금"
            },
            {
                "query": "최근 3년간 과태료",
                "expected_recent_years": 3,
                "expected_action": "과태료"
            },
            {
                "query": "그 큰 사건 있잖아",  # 모호함
                "should_fail": True  # 구체적 조건 없으므로 실패해야 함
            }
        ]
        
        accuracy_score = 0
        total_tests = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            query = test_case["query"]
            print(f"[테스트 {i}] 쿼리: '{query}'")
            
            # Rule-based 분석
            analyzed = engine._analyze_query(query)
            sql_candidates = engine._rule_based_conversion(analyzed)
            
            if sql_candidates:
                result = engine._execute_and_validate_sql(sql_candidates[0])
                
                if result['success']:
                    results = result['data']
                    print(f"  결과: {len(results)}건")
                    
                    # 정확도 검증
                    is_accurate = True
                    
                    # 실패해야 하는 경우
                    if test_case.get('should_fail'):
                        if len(results) > 0:
                            print("  ❌ 실패해야 하는데 결과가 나옴 (부정확)")
                            is_accurate = False
                        else:
                            print("  ✅ 정확히 실패함")
                    else:
                        # 성공해야 하는 경우
                        if len(results) == 0:
                            print("  ❌ 결과가 없음 (부정확)")
                            is_accurate = False
                        else:
                            # 구체적 조건 검증
                            first_result = results[0]
                            
                            # 엔티티명 검증
                            if 'should_contain' in test_case:
                                entity_name = str(first_result.get('entity_name', ''))
                                if test_case['should_contain'] not in entity_name:
                                    print(f"  ❌ 엔티티 불일치: 예상'{test_case['should_contain']}' vs 실제'{entity_name}'")
                                    is_accurate = False
                                else:
                                    print(f"  ✅ 엔티티 일치: '{entity_name}'")
                            
                            # 금액 조건 검증
                            if 'expected_min_amount' in test_case:
                                fine_amount = first_result.get('fine_amount', 0) or 0
                                if fine_amount < test_case['expected_min_amount']:
                                    print(f"  ❌ 금액 조건 불일치: 예상>={test_case['expected_min_amount']} vs 실제{fine_amount}")
                                    is_accurate = False
                                else:
                                    print(f"  ✅ 금액 조건 일치: {fine_amount}")
                            
                            # 조치 유형 검증
                            if 'expected_action' in test_case:
                                action_type = str(first_result.get('action_type', ''))
                                if test_case['expected_action'] not in action_type:
                                    print(f"  ❌ 조치유형 불일치: 예상'{test_case['expected_action']}' vs 실제'{action_type}'")
                                    is_accurate = False
                                else:
                                    print(f"  ✅ 조치유형 일치: '{action_type}'")
                    
                    if is_accurate:
                        accuracy_score += 1
                        print("  🎯 정확도: 정확")
                    else:
                        print("  🎯 정확도: 부정확")
                
                else:
                    print(f"  ❌ SQL 실행 실패: {result.get('error')}")
            else:
                print("  ❌ SQL 생성 실패")
            
            print()  # 빈 줄
        
        # 정확도 계산
        accuracy_percentage = (accuracy_score / total_tests) * 100
        
        print("=" * 60)
        print(f"🎯 Rule-based 정확도 평가 결과:")
        print(f"  정확한 응답: {accuracy_score}/{total_tests}")
        print(f"  정확도: {accuracy_percentage:.1f}%")
        
        print(f"\n💡 결론:")
        if accuracy_percentage < 70:
            print("  ❌ Rule-based 방식만으로는 부족합니다")
            print("  📝 AI 기반 NL2SQL이 반드시 필요합니다")
            print("  🔧 현재 시스템은 너무 관대하게 결과를 반환합니다")
        else:
            print("  ✅ Rule-based 방식으로도 충분합니다")
        
        # AI 보완 필요성 분석
        print(f"\n🤖 AI 보완이 필요한 영역:")
        print("  • 오타/철자 수정 (과테료 → 과태료)")
        print("  • 구어체 자연어 처리 (요즘에, 좀 보여줘)")
        print("  • 모호한 표현 해석 (그 큰 사건)")
        print("  • 암시적 조건 추론 (신한은행이 → entity_name LIKE '%신한%')")
        print("  • 복잡한 비교/분석 쿼리")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_accuracy())