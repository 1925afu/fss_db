#!/usr/bin/env python3
"""
다양한 사용자 표현 방식 테스트 스크립트
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.nl2sql_engine import NL2SQLEngine
from app.services.search_service import SearchService

async def test_diverse_user_queries():
    """다양한 사용자 표현 방식 테스트"""
    
    print("=== 다양한 사용자 표현 방식 테스트 ===\n")
    
    # 데이터베이스 연결
    db = SessionLocal()
    
    try:
        nl2sql_engine = NL2SQLEngine(db)
        search_service = SearchService(db)
        
        # 다양한 표현 방식 분류
        test_categories = {
            "기본적인 질문 (Rule-based로 처리 가능)": [
                "최근 3년간 과태료 부과 사례",
                "1억원 이상 과징금 부과 사례", 
                "공인회계사 독립성 위반 사례",
                "2025년 은행 업권 제재 현황"
            ],
            
            "구어체/자연스러운 표현 (AI 필요)": [
                "요즘에 벌금 많이 나온 회사들 좀 보여줘",
                "작년에 처벌받은 은행들이 궁금해",
                "회계사들이 문제일으킨 사건들 찾아줘",
                "돈 많이 낸 회사 순서대로 보고싶어"
            ],
            
            "복잡한 조건문 (AI 필요)": [
                "신한은행이 2025년에 받은 모든 제재를 시간순으로 정리해줘",
                "과징금이 5천만원 이상이면서 금융투자업권인 사례만 골라줘", 
                "직무정지를 받은 회계사 중에서 독립성 위반과 관련된 케이스는?",
                "보험회사 중에서 최근 2년간 과태료를 가장 많이 낸 곳은?"
            ],
            
            "비교/분석 요청 (AI 필요)": [
                "은행과 보험회사 중 어디가 제재를 더 많이 받았나?",
                "2024년과 2025년 과징금 총액을 비교해줘",
                "어떤 법률이 가장 많이 위반되었는지 순위를 매겨줘",
                "업권별로 평균 벌금액이 어떻게 다른지 보여줘"
            ],
            
            "모호한 표현 (AI + 추론 필요)": [
                "그 큰 사건 있잖아, 그거 관련 자료 좀",
                "요즘 이슈되는 가상자산 관련 문제들",
                "금감원에서 제일 크게 처벌한 사건",
                "최근에 뉴스에 나온 그 회계법인 사건"
            ],
            
            "통계/집계 요청 (부분적 Rule-based 가능)": [
                "연도별 제재 건수 트렌드를 그래프로 보여줘",
                "업권별 과징금 총액 순위 TOP 10",
                "법률 위반 유형별 분포도를 원차트로",
                "월별 제재 발생 패턴 분석"
            ],
            
            "틀린 용어/오타 포함 (AI 필요)": [
                "과테료 부과 사례들",  # 과태료 오타
                "금융투자법 위반 케이스",  # 정확히는 자본시장법
                "회게사 처벌 현황",  # 회계사 오타  
                "신한은향 제재 이력"  # 신한은행 오타
            ]
        }
        
        total_success = 0
        total_queries = 0
        category_stats = {}
        
        for category, queries in test_categories.items():
            print(f"\n📋 {category}")
            print("-" * 60)
            
            category_success = 0
            
            for i, query in enumerate(queries, 1):
                total_queries += 1
                print(f"\n[{i}] 쿼리: '{query}'")
                
                try:
                    # NL2SQL 엔진으로 직접 변환 시도
                    result = await nl2sql_engine.convert_natural_language_to_sql(query)
                    
                    if result['success'] and result['results']:
                        print(f"✅ Rule-based 성공: {len(result['results'])}건")
                        category_success += 1
                        total_success += 1
                        
                        # 생성된 SQL 확인
                        if 'sql_query' in result:
                            sql_preview = result['sql_query'].replace('\n', ' ')[:80]
                            print(f"   SQL: {sql_preview}...")
                    
                    elif result['success'] and not result['results']:
                        print(f"✅ Rule-based 성공: 0건 (조건에 맞는 데이터 없음)")
                        category_success += 1
                        total_success += 1
                    
                    else:
                        # 폴백 결과 확인
                        fallback = result.get('fallback_results', {})
                        if fallback.get('success'):
                            print(f"🔄 Fallback 성공: {len(fallback.get('results', []))}건")
                            category_success += 1
                            total_success += 1
                        else:
                            print(f"❌ 실패: {result.get('error', '알 수 없는 오류')}")
                            
                            # 검색 서비스로 최종 시도
                            try:
                                search_result = await search_service.natural_language_search(query, 3)
                                if search_result.get('results'):
                                    print(f"🔄 최종 텍스트 검색 성공: {search_result['returned_count']}건")
                                    category_success += 1
                                    total_success += 1
                                else:
                                    print("❌ 모든 방법 실패")
                            except Exception as e2:
                                print(f"❌ 최종 검색도 실패: {e2}")
                
                except Exception as e:
                    print(f"❌ 오류 발생: {e}")
            
            success_rate = (category_success / len(queries)) * 100
            category_stats[category] = {
                'success': category_success,
                'total': len(queries),
                'rate': success_rate
            }
            
            print(f"\n📊 {category} 성공률: {category_success}/{len(queries)} ({success_rate:.1f}%)")
        
        # 전체 결과 요약
        print(f"\n\n🎯 전체 테스트 결과 요약")
        print("=" * 70)
        print(f"총 성공률: {total_success}/{total_queries} ({(total_success/total_queries)*100:.1f}%)")
        
        print(f"\n📈 카테고리별 성공률:")
        for category, stats in category_stats.items():
            print(f"  • {category}: {stats['rate']:.1f}% ({stats['success']}/{stats['total']})")
        
        # Rule-based vs AI 필요도 분석
        print(f"\n🔍 Rule-based 처리 가능성 분석:")
        rule_friendly = ["기본적인 질문", "통계/집계 요청"]
        ai_needed = ["구어체/자연스러운 표현", "복잡한 조건문", "비교/분석 요청", "모호한 표현", "틀린 용어/오타 포함"]
        
        rule_based_success = sum(category_stats[cat]['success'] for cat in category_stats if any(rf in cat for rf in rule_friendly))
        rule_based_total = sum(category_stats[cat]['total'] for cat in category_stats if any(rf in cat for rf in rule_friendly))
        
        ai_success = sum(category_stats[cat]['success'] for cat in category_stats if any(ai in cat for ai in ai_needed))
        ai_total = sum(category_stats[cat]['total'] for cat in category_stats if any(ai in cat for ai in ai_needed))
        
        print(f"  • Rule-based 적합 쿼리: {rule_based_success}/{rule_based_total} ({(rule_based_success/rule_based_total)*100:.1f}%)")
        print(f"  • AI 필요 쿼리: {ai_success}/{ai_total} ({(ai_success/ai_total)*100:.1f}%)")
        
        print(f"\n💡 결론:")
        if (ai_success/ai_total) < 0.7:
            print("  • AI 기반 NL2SQL 엔진이 반드시 필요합니다")
            print("  • Rule-based만으로는 사용자 요구사항을 충족하기 어렵습니다")
        else:
            print("  • 현재 시스템으로도 대부분의 쿼리 처리 가능합니다")
            
    finally:
        db.close()
    
    print("\n=== 다양한 표현 방식 테스트 완료 ===")

if __name__ == "__main__":
    asyncio.run(test_diverse_user_queries())