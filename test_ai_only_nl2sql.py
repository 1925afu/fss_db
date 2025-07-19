#!/usr/bin/env python3
"""
AI 전용 NL2SQL 시스템 종합 테스트
사용자 제시 6가지 카테고리 50개 실제 질문
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
from app.services.ai_only_nl2sql_engine import AIOnlyNL2SQLEngine
from app.services.search_service import SearchService

async def test_ai_only_nl2sql_comprehensive():
    """AI 전용 NL2SQL 시스템 종합 테스트"""
    
    print("=== AI 전용 NL2SQL 시스템 종합 테스트 ===\n")
    
    # 데이터베이스 연결
    db = SessionLocal()
    
    try:
        ai_engine = AIOnlyNL2SQLEngine(db)
        search_service = SearchService(db)
        
        # 사용자 제시 6가지 카테고리 실제 질문들
        test_categories = {
            "1. 특정 대상 조회 (회사/개인/업권)": [
                "엔에이치아문디자산운용 제재 내역 보여줘",
                "한국대성자산운용이 받은 조치 내용 알려줘",
                "최근 3년간 삼성증권이 받은 금융위 제재 있어?",
                "인덕회계법인 소속 회계사가 징계받은 사례 찾아줘",
                "OOO 대표이사가 받은 과징금 액수는 얼마야?",
                "최근 1년간 제재받은 자산운용사 목록을 알려줘",
                "저축은행 관련 제재 현황을 찾아줘",
                "4대 회계법인(빅4)이 받은 징계 내역이 있는지 확인해줘",
                "증권사 애널리스트가 제재받은 사례가 있어?",
                "전직 임직원이 제재 대상이 된 의결서를 검색해줘"
            ],
            
            "2. 위반 행위 유형별 조회": [
                "임직원 금융투자상품 매매제한 위반 사례 보여줘",
                "회계처리 기준 위반으로 제재받은 회사 목록 좀 줘",
                "독립성 유지 의무를 위반한 공인회계사 징계 사례를 찾아줘",
                "준법감시인 선임 보고의무 위반으로 과태료를 받은 곳이 어디야?",
                "불공정거래행위 관련 제재 내용을 검색해줘",
                "내부통제 기준 마련 의무 위반으로 기관경고 받은 사례가 있어?",
                "신주인수권부사채(BW) 관련 회계부정 사건 찾아줘",
                "자본시장법 제63조 위반 사례를 검색해줘",
                "공시 의무 위반으로 제재받은 상장사 목록 알려줘",
                "고객 정보 유출과 관련된 제재가 있었는지 알려줘"
            ],
            
            "3. 조치 내용/수준별 조회": [
                "과징금 10억 원 이상 부과된 사건 목록 보여줘",
                "과태료 처분을 받은 금융회사들을 알려줘",
                "최근 2년간 '직무정지' 징계를 받은 공인회계사가 누구야?",
                "'기관경고' 조치를 받은 사례를 모두 찾아줘",
                "가장 높은 과징금을 부과받은 사건은 뭐야?",
                "과징금 액수 순서대로 작년 제재 현황을 정렬해줘",
                "1억 원 이하의 과태료가 부과된 경미한 위반 사례를 찾아줘",
                "대표이사 해임 권고 조치가 있었던 사례를 검색해줘",
                "영업정지 처분을 받은 회사가 있는지 알려줘",
                "과징금과 과태료가 동시에 부과된 사례를 찾아줘"
            ],
            
            "4. 기간 및 시점 기반 조회": [
                "2024년에 있었던 모든 제재 의결 내용을 보여줘",
                "작년 4분기에 나온 금융위 의결서 목록 좀 줘",
                "가장 최근에 올라온 제재 공시 내용은 뭐야?",
                "2023년 1월부터 6월까지 제재받은 기관은 어디야?",
                "지난 3년간 제재 건수 추이를 알려줘"
            ],
            
            "5. 복합 조건 조회 (2개 이상 조건 결합)": [
                "작년에 회계처리 위반으로 과징금을 받은 코스닥 상장사를 알려줘",
                "증권사 임직원이 미신고 계좌로 주식 매매해서 징계받은 사례 찾아줘",
                "자산운용사가 자본시장법 위반으로 1억 원 이상 과징금을 받은 사례를 최근 3년간 검색해줘",
                "감사절차 소홀로 회계법인이 제재받은 의결서와 해당 회사를 알려줘",
                "대표이사가 직접 연루된 불공정거래 사건 중 과징금이 5억 이상인 건을 찾아줘",
                "2024년에 '독립성 위반'으로 '직무정지'를 받은 회계사가 있는지 알려줘",
                "OOOO회사에 부과된 과징금 741.3백만원에 대한 의결서 원문을 보여줘",
                "'금융회사의 지배구조에 관한 법률' 위반으로 과태료 처분을 받은 기관 목록과 그 사유를 알려줘",
                "내부자 정보를 이용해 부당이득을 취한 임직원 제재 사례를 찾아줘",
                "CB나 BW 같은 메자닌 증권 관련 회계부정으로 제재받은 회사를 전부 알려줘"
            ],
            
            "6. 요약 및 통계성 조회": [
                "최근 3년간 가장 빈번하게 발생한 위반 유형은 뭐야?",
                "엔에이치아문디자산운용 제재 사건의 핵심 내용을 요약해줘",
                "작년에 부과된 총 과징금 액수는 얼마야?",
                "업권별(은행, 증권, 보험 등) 제재 건수를 비교해줘",
                "가장 많은 제재를 받은 상위 5개 금융회사는 어디야?"
            ]
        }
        
        # 테스트 결과 수집
        total_tests = 0
        total_success = 0
        category_results = {}
        
        for category, queries in test_categories.items():
            print(f"\n📋 {category}")
            print("=" * 80)
            
            category_success = 0
            category_total = len(queries)
            category_details = []
            
            for i, query in enumerate(queries, 1):
                total_tests += 1
                print(f"\n[{i}] 질문: '{query}'")
                
                try:
                    # AI 전용 엔진으로 처리
                    result = await ai_engine.process_natural_query(query, limit=5)
                    
                    if result['success']:
                        results_count = len(result['results'])
                        query_type = result.get('query_type', 'unknown')
                        model_used = result.get('metadata', {}).get('model_used', 'unknown')
                        
                        print(f"✅ 성공: {results_count}건 (유형: {query_type}, 모델: {model_used})")
                        
                        if results_count > 0:
                            # 첫 번째 결과 샘플 표시
                            first_result = result['results'][0]
                            if 'title' in first_result:
                                title = first_result['title'][:50] + "..." if len(first_result['title']) > 50 else first_result['title']
                                print(f"   샘플: {title}")
                            elif 'entity_name' in first_result:
                                print(f"   샘플: {first_result['entity_name']}")
                        else:
                            print(f"   결과: 조건에 맞는 데이터 없음 (정상)")
                        
                        category_success += 1
                        total_success += 1
                        
                        category_details.append({
                            'query': query,
                            'success': True,
                            'results_count': results_count,
                            'query_type': query_type
                        })
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        print(f"❌ 실패: {error_msg}")
                        
                        category_details.append({
                            'query': query,
                            'success': False,
                            'error': error_msg
                        })
                        
                        # 폴백 검색 시도
                        try:
                            fallback_result = await search_service.natural_language_search(query, 3)
                            if fallback_result.get('results'):
                                print(f"🔄 폴백 성공: {fallback_result['returned_count']}건")
                        except Exception as fb_e:
                            print(f"🔄 폴백도 실패: {fb_e}")
                    
                except Exception as e:
                    print(f"❌ 오류 발생: {e}")
                    category_details.append({
                        'query': query,
                        'success': False,
                        'error': str(e)
                    })
            
            # 카테고리별 결과 정리
            success_rate = (category_success / category_total) * 100
            category_results[category] = {
                'success_count': category_success,
                'total_count': category_total,
                'success_rate': success_rate,
                'details': category_details
            }
            
            print(f"\n📊 {category} 결과: {category_success}/{category_total} ({success_rate:.1f}%)")
        
        # 전체 결과 요약
        print(f"\n\n🎯 AI 전용 NL2SQL 시스템 종합 평가")
        print("=" * 80)
        
        overall_success_rate = (total_success / total_tests) * 100
        print(f"전체 성공률: {total_success}/{total_tests} ({overall_success_rate:.1f}%)")
        
        print(f"\n📈 카테고리별 성공률:")
        for category, results in category_results.items():
            print(f"  • {category}: {results['success_rate']:.1f}% ({results['success_count']}/{results['total_count']})")
        
        # 질의 유형별 분석
        type_stats = {}
        for category, results in category_results.items():
            for detail in results['details']:
                if detail['success']:
                    query_type = detail.get('query_type', 'unknown')
                    if query_type not in type_stats:
                        type_stats[query_type] = {'success': 0, 'total': 0}
                    type_stats[query_type]['success'] += 1
                    type_stats[query_type]['total'] += 1
                else:
                    if 'unknown' not in type_stats:
                        type_stats['unknown'] = {'success': 0, 'total': 0}
                    type_stats['unknown']['total'] += 1
        
        print(f"\n🔍 질의 유형별 성공률:")
        for query_type, stats in type_stats.items():
            success_rate = (stats['success'] / stats['total']) * 100 if stats['total'] > 0 else 0
            print(f"  • {query_type}: {success_rate:.1f}% ({stats['success']}/{stats['total']})")
        
        # 성능 평가
        print(f"\n💡 평가 결과:")
        if overall_success_rate >= 85:
            print("  🟢 우수: AI 전용 시스템이 매우 잘 작동합니다")
        elif overall_success_rate >= 70:
            print("  🟡 양호: AI 전용 시스템이 대체로 잘 작동합니다")
        elif overall_success_rate >= 50:
            print("  🟠 보통: AI 전용 시스템에 일부 개선이 필요합니다")
        else:
            print("  🔴 미흡: AI 전용 시스템에 대폭적인 개선이 필요합니다")
        
        # 개선 제안
        failed_categories = [cat for cat, res in category_results.items() if res['success_rate'] < 70]
        if failed_categories:
            print(f"\n🔧 개선 필요 영역:")
            for cat in failed_categories:
                print(f"  • {cat}")
        
        print(f"\n✨ AI 전용 시스템 특징:")
        print(f"  • Gemini-2.5-Flash-Lite 모델 사용")
        print(f"  • Rule-based 로직 완전 제거")
        print(f"  • 6가지 질의 유형 자동 분류")
        print(f"  • 실시간 SQL 안전성 검증")
        print(f"  • AI 자체 오류 수정 기능")
        
    finally:
        db.close()
    
    print("\n=== AI 전용 NL2SQL 시스템 종합 테스트 완료 ===")

if __name__ == "__main__":
    asyncio.run(test_ai_only_nl2sql_comprehensive())