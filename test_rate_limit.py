#!/usr/bin/env python3
"""
Rate limit 처리 로직 테스트 스크립트
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from app.services.gemini_service import GeminiService
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_rate_limit():
    """Rate limit 처리 로직 테스트"""
    
    gemini_service = GeminiService()
    
    # 간단한 테스트 프롬프트들
    test_prompts = [
        "안녕하세요를 영어로 번역해주세요.",
        "1+1의 결과를 알려주세요.", 
        "파이썬이란 무엇인가요?",
        "AI의 장점을 하나만 말해주세요.",
        "오늘 날씨가 좋다를 영어로 번역해주세요."
    ]
    
    print("=== Rate Limit 처리 로직 테스트 시작 ===")
    print(f"테스트할 요청 수: {len(test_prompts)}개")
    print(f"Rate limit: {gemini_service.rate_limit_requests_per_minute}회/분")
    print()
    
    start_time = asyncio.get_event_loop().time()
    
    for i, prompt in enumerate(test_prompts, 1):
        try:
            print(f"[{i}/{len(test_prompts)}] 요청 시작: {prompt}")
            
            # Rate limit이 적용된 API 요청
            response = await gemini_service._make_api_request_with_rate_limit(prompt)
            
            print(f"✅ 응답 받음: {response[:50]}...")
            print(f"현재 요청 기록 수: {len(gemini_service.request_timestamps)}")
            print()
            
        except Exception as e:
            print(f"❌ 요청 실패: {str(e)}")
            print()
    
    end_time = asyncio.get_event_loop().time()
    total_time = end_time - start_time
    
    print("=== 테스트 완료 ===")
    print(f"총 소요 시간: {total_time:.1f}초")
    print(f"평균 요청 간격: {total_time/len(test_prompts):.1f}초")

if __name__ == '__main__':
    asyncio.run(test_rate_limit())