"""
프론트엔드-백엔드 통합 테스트
"""

import requests
import time
import json

# 서버 URL
FRONTEND_URL = "http://localhost:3000"
API_URL = "http://localhost:8000/api/v1"

def test_servers_running():
    """서버 상태 확인"""
    print("1. 서버 상태 확인")
    print("-" * 50)
    
    # 백엔드 API 확인
    try:
        response = requests.get(f"{API_URL}/search/stats")
        if response.status_code == 200:
            print("✅ 백엔드 API 서버: 정상 작동")
            stats = response.json()
            print(f"   - 의결서: {stats['totals']['decisions']}건")
            print(f"   - 조치: {stats['totals']['actions']}건")
            print(f"   - 법률: {stats['totals']['laws']}건")
        else:
            print("❌ 백엔드 API 서버: 응답 오류")
    except Exception as e:
        print(f"❌ 백엔드 API 서버: 연결 실패 - {e}")
    
    # 프론트엔드 확인
    try:
        response = requests.get(FRONTEND_URL)
        if response.status_code == 200:
            print("✅ 프론트엔드 서버: 정상 작동")
            print("   - Next.js 서버가 포트 3000에서 실행 중")
        else:
            print("❌ 프론트엔드 서버: 응답 오류")
    except Exception as e:
        print(f"❌ 프론트엔드 서버: 연결 실패 - {e}")

def test_api_endpoints():
    """주요 API 엔드포인트 테스트"""
    print("\n2. API 엔드포인트 테스트")
    print("-" * 50)
    
    # NL2SQL 테스트
    try:
        response = requests.post(
            f"{API_URL}/search/nl2sql",
            json={"query": "2025년 과태료 사례", "limit": 3}
        )
        if response.status_code == 200:
            result = response.json()
            print("✅ NL2SQL 검색: 정상 작동")
            print(f"   - 결과: {result['count']}건 검색됨")
        else:
            print("❌ NL2SQL 검색: 오류")
    except Exception as e:
        print(f"❌ NL2SQL 검색: 실패 - {e}")
    
    # 검색 제안 테스트
    try:
        response = requests.get(f"{API_URL}/search/suggestions")
        if response.status_code == 200:
            suggestions = response.json()
            print("✅ 검색 제안: 정상 작동")
            print(f"   - 키워드: {len(suggestions.get('basic_keywords', []))}개")
            print(f"   - 추천 쿼리: {len(suggestions.get('common_queries', []))}개")
        else:
            print("❌ 검색 제안: 오류")
    except Exception as e:
        print(f"❌ 검색 제안: 실패 - {e}")

def test_integration_flow():
    """통합 플로우 테스트"""
    print("\n3. 통합 플로우 테스트")
    print("-" * 50)
    
    test_queries = [
        "신한은행 제재",
        "1억원 이상 과징금",
        "2025년 의결서"
    ]
    
    for query in test_queries:
        try:
            response = requests.post(
                f"{API_URL}/search/nl2sql",
                json={"query": query, "limit": 5}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"✅ '{query}' 검색 성공")
                print(f"   - 결과: {result['count']}건")
                if result['count'] > 0:
                    first = result['results']['results'][0]
                    print(f"   - 첫 결과: {first.get('title', 'N/A')}")
            else:
                print(f"❌ '{query}' 검색 실패")
        except Exception as e:
            print(f"❌ '{query}' 검색 오류: {e}")
        
        time.sleep(0.5)  # API 부하 방지

def main():
    print("FSC 의결서 검색 시스템 통합 테스트")
    print("=" * 50)
    print(f"프론트엔드: {FRONTEND_URL}")
    print(f"백엔드 API: {API_URL}")
    print("=" * 50)
    
    test_servers_running()
    test_api_endpoints()
    test_integration_flow()
    
    print("\n" + "=" * 50)
    print("테스트 완료!")
    print("\n웹 브라우저에서 다음 주소로 접속하세요:")
    print(f"👉 {FRONTEND_URL}")
    print("\n주요 기능:")
    print("- 자연어 검색: 한국어로 질문하면 AI가 의결서를 검색")
    print("- 대시보드: 실시간 통계 및 최근 의결서 확인")
    print("- 고급 검색: 카테고리, 업권, 연도별 필터링")

if __name__ == "__main__":
    main()