# FSS 규제 인텔리전스 플랫폼

금융위원회(FSC) 의결서 데이터를 수집, 분석, 구조화하여 자연어 질의를 통해 복합적인 규제 동향 및 제재 사례를 분석할 수 있는 웹 기반 시스템입니다.

## 🚀 주요 기능

- **FSC 의결서 자동 수집**: 금융위원회 홈페이지에서 의결서 자동 다운로드
- **하이브리드 PDF 처리**: Rule-based 패턴 매칭 + AI 보완으로 최적화된 구조화
  - Rule-based: 한국어 의결서 표준 패턴 추출 (95%+ 정확도)
  - AI 보완: 복잡한 위반 내용 요약 및 카테고리 분류
- **복합키 데이터베이스**: 연도별 의결번호 중복을 처리하는 고도화된 스키마
- **법률 정보 매핑**: Action-Law 다대다 관계를 통한 정교한 법적 근거 추적
- **자연어 쿼리**: 한국어 자연어를 SQL로 변환하여 복합적인 분석 가능
- **웹 인터페이스**: FastAPI 기반 REST API 및 검색 기능

## 📅 개발 진행 현황

### ✅ 완료된 핵심 기능 (2025년 7월 기준)
- [x] **기본 환경 설정**: Python 가상환경, 의존성 관리, 프로젝트 구조
- [x] **FSC 크롤러**: 2021-2025년 의결서 자동 수집 (2,000+ 파일)
- [x] **고도화된 데이터베이스**: 복합키 스키마 (decision_year + decision_id)
- [x] **Rule-based 추출기**: 한국어 의결서 패턴 분석으로 95%+ 정확도 달성
- [x] **하이브리드 처리 시스템**: Rule-based + AI 보완 아키텍처
- [x] **법률 정보 매핑**: ActionLawMap을 통한 조치-법률 연결
- [x] **PDF 처리 엔진**: 파일명 기반 의결번호 추출 및 데이터 품질 검증
- [x] **FastAPI 백엔드**: REST API 구조 및 서비스 레이어
- [x] **Gemini API Rate Limiting**: Free tier 호환 (10 requests/min)
- [x] **대규모 배치 처리**: 2025년 83개 의결서 성공적으로 DB화 (96.4% 성공률)

### 🎯 실제 처리 성과
- **83개 2025년 의결서** 완전 처리 완료
- **84개 조치 항목** 추출 및 분류
- **43개 법률 항목** 자동 매핑
- **제1호~제200호** 의결서 범위 커버

### 🚧 진행 중
- [ ] **웹 인터페이스**: Next.js 프론트엔드 구현
- [ ] **NL2SQL 엔진**: 자연어 쿼리 변환 기능

### 📋 예정 작업
- [ ] **성능 최적화**: 대용량 데이터 처리 및 인덱싱
- [ ] **시각화 대시보드**: 규제 동향 분석 차트
- [ ] **배포 환경**: Docker 컨테이너화 및 CI/CD

## 📋 시스템 요구사항

- Python 3.11+
- PostgreSQL 15+ (개발 단계에서는 SQLite 사용)
- Google Gemini API 키

## 🛠️ 설치 및 설정

### 1. 저장소 클론
```bash
git clone <repository-url>
cd fss_db
```

### 2. 가상환경 설정
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치
```bash
pip install -r requirements-core.txt
```

### 4. 환경 변수 설정
```bash
cp .env.example .env
# .env 파일을 편집하여 Google Gemini API 키 설정
```

### 5. 데이터베이스 초기화
```bash
python -c "from app.core.database import init_db; init_db()"
```

## 🔧 사용 방법

### 1. 웹 서버 실행
```bash
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

서버 실행 후 http://localhost:8000 에서 접근 가능

### 2. FSC 의결서 크롤링
```bash
source venv/bin/activate
python scripts/crawler.py --start-date 2024-01-01 --end-date 2024-12-31
```

### 3. PDF 파일 처리 (배치)
```bash
source venv/bin/activate
python process_2025_batch.py  # 2025년 의결서 전체 처리
```

### 4. 단일 PDF 파일 처리
```bash
source venv/bin/activate
python scripts/process_pdfs.py --single-file /path/to/decision.pdf
```

### 5. 처리 통계 확인
```bash
source venv/bin/activate
python -c "
from app.core.database import SessionLocal
from app.models.fsc_models import Decision, Action, Law
db = SessionLocal()
print(f'의결서: {db.query(Decision).count()}개')
print(f'조치: {db.query(Action).count()}개')  
print(f'법률: {db.query(Law).count()}개')
db.close()
"
```

## 📊 API 엔드포인트

### 의결서 관련
- `GET /api/v1/decisions/` - 의결서 목록 조회
- `GET /api/v1/decisions/{id}` - 특정 의결서 상세 조회
- `GET /api/v1/decisions/{id}/actions` - 의결서 관련 조치 목록
- `GET /api/v1/decisions/stats/categories` - 카테고리별 통계

### 검색 관련
- `POST /api/v1/search/nl2sql` - 자연어 쿼리 검색
- `POST /api/v1/search/text` - 전문 텍스트 검색
- `GET /api/v1/search/suggestions` - 검색 제안

## 🔍 자연어 쿼리 예시

```json
{
  "query": "최근 3년간 과태료 부과 사례"
}
```

```json
{
  "query": "공인회계사 독립성 위반으로 직무정지 징계를 받은 사례"
}
```

```json
{
  "query": "1억원 이상 과징금 부과 사례를 최근 순으로 보여줘"
}
```

## 🗂️ 데이터베이스 구조

### Decisions (의결서) - 복합 Primary Key
- **복합키**: `(decision_year, decision_id)` - 연도별 의결번호 중복 해결
- **날짜 분해**: `decision_month, decision_day` - 효율적인 날짜 검색
- **분류 체계**: category_1 (제재/인허가/정책), category_2 (기관/임직원/전문가)
- **전문 검색**: full_text 필드를 통한 키워드 검색

### Actions (조치) - 복합 Foreign Key
- **복합 외래키**: `(decision_year, decision_id)` 참조
- **정규화된 데이터**: entity_name, industry_sector, violation_details
- **금액 처리**: fine_amount (BigInteger), 한국어 단위 자동 변환
- **법률 연결**: ActionLawMap을 통한 다대다 관계

### Laws (법률)
- **정규화**: law_name (정식명칭), law_short_name (약칭)
- **분류**: law_category (업권법/공통법 등)
- **중복 방지**: 약칭 기반 기존 법률 검색

### ActionLawMap (조치-법률 매핑)
- **다대다 관계**: 하나의 조치가 여러 법률 조항 참조 가능
- **상세 조항**: article_details (제35조 제1항)
- **조항 요약**: article_purpose (법적 근거 설명)

## 📝 개발 가이드

### 프로젝트 구조
```
fss_db/
├── app/
│   ├── api/v1/endpoints/     # API 엔드포인트
│   ├── core/                 # 핵심 설정 및 데이터베이스
│   ├── models/              # 데이터베이스 모델
│   └── services/            # 비즈니스 로직
├── scripts/                 # 실행 스크립트
├── prompts/                 # Gemini API 프롬프트
├── data/                    # 데이터 파일
└── tests/                   # 테스트 파일
```

### 새로운 기능 추가
1. 모델 정의: `app/models/`
2. 서비스 로직: `app/services/`
3. API 엔드포인트: `app/api/v1/endpoints/`
4. 테스트 작성: `tests/`

## 🧪 테스트

### 크롤러 테스트
```bash
python test_crawler.py
```

### 단위 테스트
```bash
pytest tests/
```

## 🔐 보안 고려사항

- API 키는 환경 변수로 관리
- 사용자 입력 검증 및 SQL 인젝션 방지
- 파일 업로드 시 보안 검증
- 로그에 민감한 정보 기록 금지

## 📈 성능 최적화

- 데이터베이스 인덱스 최적화
- 쿼리 결과 캐싱
- 비동기 처리 활용
- 파일 처리 배치 최적화

## 🚨 문제 해결

### 크롤링 실패
- 네트워크 연결 확인
- FSC 웹사이트 구조 변경 확인
- 사용자 에이전트 및 요청 헤더 확인

### PDF 처리 오류
- Google Gemini API 키 확인
- PDF 파일 손상 여부 확인
- 프롬프트 파일 존재 확인

### 데이터베이스 오류
- 연결 설정 확인
- 테이블 스키마 확인
- 권한 설정 확인

## 📞 지원

문제 발생 시 다음 정보와 함께 이슈를 등록해주세요:
- 오류 메시지
- 실행 환경 정보
- 재현 단계
- 로그 파일
