#!/usr/bin/env python3
"""
API 엔드포인트 테스트 스크립트
"""

import sys
import asyncio
sys.path.append('.')

from fastapi.testclient import TestClient
from app.main import app

def test_api_endpoints():
    """API 엔드포인트 테스트"""
    print("=== API 엔드포인트 테스트 ===")
    
    client = TestClient(app)
    
    # 1. 루트 엔드포인트 테스트
    print("1. 루트 엔드포인트 테스트...")
    response = client.get("/")
    print(f"   상태코드: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   응답: {data.get('message', 'N/A')}")
        print("   ✅ 루트 엔드포인트 정상")
    else:
        print("   ❌ 루트 엔드포인트 오류")
    
    # 2. 헬스체크 엔드포인트 테스트
    print("\n2. 헬스체크 엔드포인트 테스트...")
    response = client.get("/health")
    print(f"   상태코드: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   상태: {data.get('status', 'N/A')}")
        print("   ✅ 헬스체크 엔드포인트 정상")
    else:
        print("   ❌ 헬스체크 엔드포인트 오류")
    
    # 3. API v1 의결서 목록 조회 테스트
    print("\n3. 의결서 목록 조회 테스트...")
    response = client.get("/api/v1/decisions/")
    print(f"   상태코드: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   의결서 수: {len(data)}")
        if data:
            print(f"   첫 번째 의결서: {data[0].get('title', 'N/A')}")
        print("   ✅ 의결서 목록 조회 정상")
    else:
        print("   ❌ 의결서 목록 조회 오류")
    
    # 4. 의결서 통계 조회 테스트
    print("\n4. 의결서 통계 조회 테스트...")
    response = client.get("/api/v1/decisions/stats/categories")
    print(f"   상태코드: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   대분류 통계: {len(data.get('category_1', []))}개")
        print(f"   중분류 통계: {len(data.get('category_2', []))}개")
        print("   ✅ 의결서 통계 조회 정상")
    else:
        print("   ❌ 의결서 통계 조회 오류")
        try:
            error_data = response.json()
            print(f"   오류 상세: {error_data}")
        except:
            print(f"   응답 텍스트: {response.text}")
    
    print("\n=== API 테스트 완료 ===")

if __name__ == "__main__":
    test_api_endpoints()