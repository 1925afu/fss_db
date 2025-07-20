"""
간단한 NL2SQL API 테스트
"""

import requests
import json

# API 엔드포인트
url = "http://localhost:8000/api/v1/search/nl2sql"

# 테스트 쿼리
test_query = "2025년 과태료 부과 사례를 보여줘"

# 요청 보내기
print(f"테스트 쿼리: {test_query}")
print("-" * 50)

try:
    response = requests.post(
        url,
        json={"query": test_query, "limit": 5}
    )
    
    print(f"상태 코드: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n응답 구조:")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:1000] + "...")
        
        # 주요 정보 출력
        if 'count' in result:
            print(f"\n결과 개수: {result['count']}건")
        
        if 'results' in result and result['results']:
            print(f"\n첫 번째 결과 샘플:")
            first = result['results'][0]
            print(json.dumps(first, indent=2, ensure_ascii=False)[:500])
    else:
        print(f"오류: {response.text}")
        
except Exception as e:
    print(f"예외 발생: {e}")