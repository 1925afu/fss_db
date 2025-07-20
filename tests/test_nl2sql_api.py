"""
NL2SQL API 테스트 스크립트
"""

import requests
import json
from typing import Dict, List, Any
from datetime import datetime
import time

class NL2SQLTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.nl2sql_endpoint = f"{base_url}/api/v1/search/nl2sql"
        self.test_results = []
    
    def test_query(self, query: str, expected_type: str = None) -> Dict[str, Any]:
        """단일 쿼리 테스트"""
        print(f"\n{'='*60}")
        print(f"테스트 쿼리: {query}")
        print(f"예상 유형: {expected_type}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            response = requests.post(
                self.nl2sql_endpoint,
                json={"query": query, "limit": 10}
            )
            
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                
                # 결과 요약 출력
                print(f"\n✅ 성공!")
                print(f"- 응답 시간: {elapsed_time:.2f}초")
                print(f"- 결과 건수: {result.get('count', 0)}건")
                
                # 실제 응답 구조에 맞게 수정
                if 'results' in result:
                    inner_result = result['results']
                    
                    # 쿼리 유형 및 SQL 출력
                    if 'query_type' in inner_result:
                        print(f"- 쿼리 유형: {inner_result['query_type']}")
                    
                    if 'sql_query' in inner_result:
                        print(f"\n생성된 SQL:")
                        print(f"  {inner_result['sql_query'][:100]}...")
                    
                    # 결과 데이터
                    if 'results' in inner_result and inner_result['results']:
                        print(f"\n첫 번째 결과:")
                        first_result = inner_result['results'][0]
                        for key, value in first_result.items():
                            print(f"  - {key}: {value}")
                    
                    # 메타데이터 확인
                    if 'metadata' in inner_result:
                        metadata = inner_result['metadata']
                        print(f"\n메타데이터:")
                        print(f"  - 사용 모델: {metadata.get('model_used', 'N/A')}")
                
                # 테스트 결과 저장
                actual_type = None
                if 'results' in result and 'query_type' in result['results']:
                    actual_type = result['results']['query_type']
                
                self.test_results.append({
                    "query": query,
                    "expected_type": expected_type,
                    "status": "success",
                    "elapsed_time": elapsed_time,
                    "result_count": result.get('count', 0),
                    "actual_type": actual_type
                })
                
                return result
                
            else:
                print(f"\n❌ 실패!")
                print(f"- 상태 코드: {response.status_code}")
                print(f"- 오류 메시지: {response.text}")
                
                self.test_results.append({
                    "query": query,
                    "expected_type": expected_type,
                    "status": "failed",
                    "elapsed_time": elapsed_time,
                    "error": response.text
                })
                
                return {"error": response.text}
                
        except Exception as e:
            print(f"\n❌ 예외 발생: {str(e)}")
            self.test_results.append({
                "query": query,
                "expected_type": expected_type,
                "status": "error",
                "error": str(e)
            })
            return {"error": str(e)}
    
    def run_all_tests(self):
        """모든 테스트 케이스 실행"""
        test_cases = [
            # 1. 특정 대상 조회
            {
                "query": "신한은행 관련 제재 내역을 보여줘",
                "type": "specific_target"
            },
            {
                "query": "회계법인 관련 조치사항",
                "type": "specific_target"
            },
            
            # 2. 위반 행위 유형별
            {
                "query": "독립성 위반 사례를 찾아줘",
                "type": "violation_type"
            },
            {
                "query": "회계처리 기준 위반 건",
                "type": "violation_type"
            },
            
            # 3. 조치 수준별
            {
                "query": "1억원 이상 과징금 부과 사례",
                "type": "action_level"
            },
            {
                "query": "직무정지 처분을 받은 사례",
                "type": "action_level"
            },
            
            # 4. 시점 기반
            {
                "query": "2025년 제재 현황",
                "type": "time_based"
            },
            {
                "query": "최근 3개월간 의결서",
                "type": "time_based"
            },
            
            # 5. 통계/요약
            {
                "query": "업권별 제재 통계를 보여줘",
                "type": "statistics"
            },
            {
                "query": "top 5 과태료 부과 사례",
                "type": "statistics"
            },
            
            # 6. 복합 조건
            {
                "query": "최근 3년간 은행업권에서 1천만원 이상 과태료 부과된 사례",
                "type": "complex_condition"
            },
            {
                "query": "2025년 보험업권 독립성 위반으로 인한 제재",
                "type": "complex_condition"
            }
        ]
        
        print("\n" + "="*80)
        print("NL2SQL API 테스트 시작")
        print("="*80)
        print(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"총 테스트 케이스: {len(test_cases)}개")
        
        for test_case in test_cases:
            self.test_query(test_case["query"], test_case["type"])
            time.sleep(1)  # API 부하 방지
        
        self.print_summary()
    
    def print_summary(self):
        """테스트 결과 요약"""
        print("\n" + "="*80)
        print("테스트 결과 요약")
        print("="*80)
        
        total = len(self.test_results)
        success = sum(1 for r in self.test_results if r["status"] == "success")
        failed = sum(1 for r in self.test_results if r["status"] in ["failed", "error"])
        
        print(f"\n전체 테스트: {total}개")
        print(f"✅ 성공: {success}개 ({success/total*100:.1f}%)")
        print(f"❌ 실패: {failed}개 ({failed/total*100:.1f}%)")
        
        # 성공한 테스트의 평균 응답 시간
        success_times = [r["elapsed_time"] for r in self.test_results 
                        if r["status"] == "success" and "elapsed_time" in r]
        if success_times:
            avg_time = sum(success_times) / len(success_times)
            print(f"\n평균 응답 시간: {avg_time:.2f}초")
        
        # 쿼리 유형 분류 정확도
        type_matches = 0
        type_checks = 0
        for r in self.test_results:
            if r["status"] == "success" and r.get("expected_type"):
                type_checks += 1
                if r.get("actual_type") == r["expected_type"]:
                    type_matches += 1
        
        if type_checks > 0:
            print(f"\n쿼리 유형 분류 정확도: {type_matches}/{type_checks} ({type_matches/type_checks*100:.1f}%)")
        
        # 실패한 테스트 상세
        if failed > 0:
            print("\n실패한 테스트:")
            for r in self.test_results:
                if r["status"] in ["failed", "error"]:
                    print(f"  - {r['query']}: {r.get('error', 'Unknown error')}")
    
    def test_edge_cases(self):
        """엣지 케이스 테스트"""
        print("\n" + "="*80)
        print("엣지 케이스 테스트")
        print("="*80)
        
        edge_cases = [
            "보여줘",  # 너무 짧은 쿼리
            "SELECT * FROM decisions",  # SQL 직접 입력
            "😀 이모지 쿼리 🏦",  # 이모지 포함
            "a" * 500,  # 너무 긴 쿼리
            "",  # 빈 쿼리
        ]
        
        for query in edge_cases:
            self.test_query(query if query else "(빈 쿼리)")


if __name__ == "__main__":
    tester = NL2SQLTester()
    
    # 기본 테스트 실행
    tester.run_all_tests()
    
    # 엣지 케이스 테스트
    # tester.test_edge_cases()
    
    # 결과를 파일로 저장
    with open("nl2sql_test_results.json", "w", encoding="utf-8") as f:
        json.dump(tester.test_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 테스트 결과가 nl2sql_test_results.json 파일에 저장되었습니다.")