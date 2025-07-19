#!/usr/bin/env python3
"""
NL2SQL 엔진 테스트 스크립트
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
from app.services.nl2sql_engine import NL2SQLEngine, QuerySuggestionEngine
from app.services.search_service import SearchService

async def test_nl2sql_engine():
    """NL2SQL 엔진 테스트"""
    
    print("=== NL2SQL 엔진 테스트 시작 ===\n")
    
    # 데이터베이스 연결
    db = SessionLocal()
    
    try:
        # NL2SQL 엔진 초기화
        nl2sql_engine = NL2SQLEngine(db)
        search_service = SearchService(db)
        suggestion_engine = QuerySuggestionEngine(db)
        
        # 테스트 쿼리들
        test_queries = [
            "최근 3년간 과태료 부과 사례",
            "공인회계사 독립성 위반 사례", 
            "1억원 이상 과징금 부과 사례",
            "2025년 은행 업권 제재 현황",
            "업권별 과징금 통계",
            "직무정지 처분을 받은 사례"
        ]
        
        print("1. Rule-based NL2SQL 테스트")
        print("-" * 50)
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n[테스트 {i}] 쿼리: '{query}'")
            
            try:
                # NL2SQL 엔진으로 변환
                result = await nl2sql_engine.convert_natural_language_to_sql(query)
                
                if result['success']:
                    print(f"✅ 성공: {result['metadata']['method']} 방식")
                    print(f"📊 결과 수: {len(result['results'])}건")
                    if result['results']:
                        print(f"🔍 첫 번째 결과: {result['results'][0]}")
                else:
                    print(f"❌ 실패: {result.get('error', '알 수 없는 오류')}")
                    if 'fallback_results' in result:
                        print(f"🔄 폴백 결과 수: {len(result['fallback_results'].get('results', []))}건")
                
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
        
        print("\n\n2. 검색 서비스 통합 테스트")
        print("-" * 50)
        
        for i, query in enumerate(test_queries[:3], 1):  # 처음 3개만 테스트
            print(f"\n[통합 테스트 {i}] 쿼리: '{query}'")
            
            try:
                # 검색 서비스로 통합 테스트
                result = await search_service.natural_language_search(query, limit=3)
                
                print(f"✅ 방식: {result['method']}")
                print(f"📊 결과 수: {result['returned_count']}/{result['total_found']}건")
                
                if result.get('results'):
                    print("🔍 결과 샘플:")
                    for j, item in enumerate(result['results'][:2], 1):
                        if isinstance(item, dict):
                            title = item.get('title', 'N/A')[:50]
                            entity = item.get('entity_name', 'N/A')
                            print(f"   {j}. {title}... ({entity})")
                
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
        
        print("\n\n3. 스마트 제안 엔진 테스트")
        print("-" * 50)
        
        try:
            suggestions = suggestion_engine.get_smart_suggestions()
            print("✅ 제안 생성 성공")
            
            for category, items in suggestions.items():
                print(f"\n📋 {category}:")
                for item in items[:3]:  # 처음 3개만 표시
                    print(f"  - {item}")
        
        except Exception as e:
            print(f"❌ 제안 생성 실패: {e}")
        
        print("\n\n4. 고급 검색 테스트")
        print("-" * 50)
        
        try:
            # 고급 필터 검색 테스트
            filters = {
                'decision_year': 2025,
                'action_type': '과태료',
                'industry_sector': '회계/감사'
            }
            
            result = await search_service.advanced_search(filters, limit=3)
            print(f"✅ 고급 검색 성공: {result['total_found']}건 발견")
            
            if result['results']:
                print("🔍 고급 검색 결과:")
                for i, item in enumerate(result['results'][:2], 1):
                    print(f"  {i}. {item.get('title', 'N/A')[:40]}...")
        
        except Exception as e:
            print(f"❌ 고급 검색 실패: {e}")
        
    finally:
        db.close()
    
    print("\n=== NL2SQL 엔진 테스트 완료 ===")

if __name__ == "__main__":
    asyncio.run(test_nl2sql_engine())