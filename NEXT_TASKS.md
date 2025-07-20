# 다음 세션에서 진행할 작업 목록

## 1. 데이터 처리 완료 (우선순위: 높음)

### 1.1 남은 2025년 의결서 처리
- **대상**: 25개 미처리 의결서 (59호~200호 중)
- **전제조건**: Gemini API 할당량 갱신 후 (매일 갱신)
- **실행 방법**:
  ```bash
  python process_2025_remaining_files.py
  ```
- **예상 소요시간**: 약 30분
- **주의사항**: 
  - 54호, 94호는 이미 SKIP_FILES로 지정됨
  - API rate limit (10 requests/min) 준수

### 1.2 문제 파일 개별 처리
- **대상**: 2025-54호, 2025-94호 (복잡한 구조로 타임아웃 발생)
- **접근 방법**: 
  - AI 2단계 파이프라인 타임아웃 연장 (3분 → 5분)
  - 또는 수동으로 핵심 정보만 추출

### 1.3 데이터 검증
- **실행**: `python verify_db_data_v2.py`
- **목적**: 정수형 금액 비교를 통한 정확도 검증

## 2. 추가 년도 데이터 처리 (우선순위: 중간)

### 2.1 2024년 의결서 처리
- **예상 파일 수**: 약 400개
- **소요 시간**: 3-4일 (API 할당량 고려)
- **배치 전략**: 일일 250개 제한 내에서 처리

### 2.2 2021-2023년 의결서 처리
- **총 파일 수**: 약 1,600개
- **소요 시간**: 2주 예상
- **고려사항**: 오래된 문서의 형식 차이 확인 필요

## 3. 쿼리 시스템 개발 (우선순위: 높음)

### 3.1 NL2SQL 엔진 구현
- **기술 스택**: LangChain + Gemini API
- **주요 기능**:
  - 한국어 자연어 쿼리 처리
  - 복합키 스키마를 고려한 SQL 생성
  - 쿼리 결과 후처리 및 포맷팅

### 3.2 API 엔드포인트 완성
- **구현 필요**:
  - `/api/v1/search/nl2sql` - 자연어 검색
  - `/api/v1/stats/*` - 통계 API
  - 페이지네이션 및 필터링

## 4. 웹 인터페이스 개발 (우선순위: 중간)

### 4.1 검색 인터페이스
- **위치**: `frontend/src/components/search/`
- **기능**:
  - 자연어 검색 입력
  - 검색 결과 테이블/카드 뷰
  - 필터 및 정렬 옵션

### 4.2 대시보드
- **위치**: `frontend/src/components/dashboard/`
- **시각화**:
  - 년도별 의결서 통계
  - 제재 유형별 분포
  - 업권별 제재 현황
  - 과태료/과징금 추이

## 5. 성능 최적화 (우선순위: 낮음)

### 5.1 데이터베이스 최적화
- 인덱스 추가
- 쿼리 최적화
- 캐싱 전략

### 5.2 API 성능 개선
- 응답 캐싱
- 비동기 처리 최적화

## 6. 배포 준비 (우선순위: 낮음)

### 6.1 Docker 컨테이너화
- Dockerfile 수정
- docker-compose 구성
- 환경 변수 관리

### 6.2 문서화
- API 문서 (Swagger/OpenAPI)
- 사용자 가이드
- 시스템 운영 매뉴얼

## 즉시 실행 가능한 명령어

```bash
# 1. 가상환경 활성화
source venv/bin/activate

# 2. 데이터베이스 상태 확인
python -c "
from app.core.database import SessionLocal
from app.models.fsc_models import Decision, Action, Law
db = SessionLocal()
print(f'의결서: {db.query(Decision).count()}개')
print(f'조치: {db.query(Action).count()}개')
print(f'법률: {db.query(Law).count()}개')
print(f'2025년 의결서: {db.query(Decision).filter(Decision.decision_year==2025).count()}개')
db.close()
"

# 3. API 서버 실행
uvicorn app.main:app --reload

# 4. 프론트엔드 개발 서버 실행
cd frontend && npm run dev
```

## 참고사항

- **Gemini API 할당량**: 
  - Free tier: 250 requests/day
  - Rate limit: 10 requests/minute
  
- **현재 처리 상태**:
  - 2025년: 58/83 (69.9%)
  - 2024년: 0/400 (0%)
  - 2023년: 0/400 (0%)
  - 2022년: 0/400 (0%)
  - 2021년: 0/400 (0%)

- **주요 파일 위치**:
  - 배치 처리: `process_2025_remaining_files.py`
  - 데이터 검증: `verify_db_data_v2.py`
  - Rule-based 추출기: `app/services/rule_based_extractor.py`
  - PDF 처리기: `app/services/pdf_processor.py`