from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 애플리케이션 기본 설정
    APP_NAME: str = "FSS 규제 인텔리전스 플랫폼"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "your_secret_key_here"
    
    # 데이터베이스 설정
    DATABASE_URL: str = "sqlite:///./fss_db.sqlite"
    DB_ECHO: bool = False
    
    # Google Gemini API 설정
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # FSC 크롤링 설정
    FSC_BASE_URL: str = "https://www.fsc.go.kr"
    DOWNLOAD_DELAY: float = 1.0
    MAX_RETRIES: int = 3
    BATCH_SIZE: int = 10
    
    # 파일 경로 설정
    DATA_DIR: str = "./data"
    RAW_ZIP_DIR: str = "./data/raw_zip"
    PROCESSED_PDF_DIR: str = "./data/processed_pdf"
    PROMPT_DIR: str = "./prompts"
    
    # API 설정
    API_V1_STR: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # 로깅 설정
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 전역 설정 인스턴스
settings = Settings()