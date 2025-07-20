"""
Gemini Structured Output 테스트 - 간단한 예제
"""
import os
import asyncio
import google.generativeai as genai
from pydantic import BaseModel, Field
from typing import List, Optional

# API 키 설정
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


# 간단한 테스트 모델
class SimpleItem(BaseModel):
    name: str = Field(description="아이템 이름")
    value: int = Field(default=0, description="아이템 값")


class SimpleResponse(BaseModel):
    title: str = Field(description="제목")
    items: List[SimpleItem] = Field(description="아이템 목록")
    count: Optional[int] = Field(default=None, description="총 개수")


async def test_simple_structured():
    """간단한 구조화된 출력 테스트"""
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = """
    다음 정보를 구조화된 형식으로 반환하세요:
    
    제목: 테스트 문서
    아이템들:
    - 사과 (가격: 1000)
    - 바나나 (가격: 500)
    - 오렌지 (가격: 800)
    """
    
    try:
        # 방법 1: Pydantic 모델 직접 사용
        print("방법 1: Pydantic 모델 직접 사용")
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=SimpleResponse,
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        print(f"응답: {response.text}")
        
    except Exception as e:
        print(f"방법 1 실패: {e}")
        
    try:
        # 방법 2: JSON Schema 직접 정의
        print("\n방법 2: JSON Schema 직접 정의")
        schema = {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "제목"
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"type": "integer"}
                        },
                        "required": ["name", "value"]
                    }
                },
                "count": {
                    "type": "integer",
                    "description": "총 개수",
                    "nullable": True
                }
            },
            "required": ["title", "items"]
        }
        
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        print(f"응답: {response.text}")
        
    except Exception as e:
        print(f"방법 2 실패: {e}")
        
    try:
        # 방법 3: 간단한 딕셔너리 스키마
        print("\n방법 3: 간단한 딕셔너리 스키마")
        simple_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"type": "number"}
                        }
                    }
                }
            }
        }
        
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=simple_schema,
        )
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        print(f"응답: {response.text}")
        
    except Exception as e:
        print(f"방법 3 실패: {e}")


if __name__ == "__main__":
    asyncio.run(test_simple_structured())