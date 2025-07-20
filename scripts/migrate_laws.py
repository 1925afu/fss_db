"""
법률 데이터 마이그레이션 스크립트
fsc_laws_with_abbreviations.json 기반으로 정규화된 법률 테이블 생성
"""
import sys
import os
import json
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.fsc_models_v2 import Base, LawV2
from app.core.config import settings

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LawMigrator:
    """법률 데이터 마이그레이션 클래스"""
    
    def __init__(self, db_path: str = None):
        # 새 데이터베이스 경로
        self.db_path = db_path or "sqlite:///fss_db_v2.sqlite"
        self.engine = create_engine(self.db_path)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # 표준 법률 데이터 파일 경로
        self.laws_json_path = "fsc_laws_with_abbreviations.json"
        
        # 기존 DB 연결 (참조용)
        self.old_db_path = "sqlite:///fss_db.sqlite"
        self.old_engine = create_engine(self.old_db_path)
        
    def create_tables(self):
        """새 데이터베이스에 테이블 생성"""
        logger.info("새 데이터베이스 테이블 생성 중...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("테이블 생성 완료")
    
    def load_standard_laws(self) -> list:
        """표준 법률 데이터 로드"""
        logger.info(f"표준 법률 데이터 로드: {self.laws_json_path}")
        
        with open(self.laws_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        laws = data.get('laws', [])
        logger.info(f"총 {len(laws)}개의 표준 법률 데이터 로드됨")
        
        return laws
    
    def create_law_mapping(self) -> dict:
        """기존 법률명과 표준 법률명 매핑 생성"""
        logger.info("법률명 매핑 테이블 생성 중...")
        
        # 기존 DB에서 사용된 법률명 조회
        with self.old_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT law_name, law_short_name 
                FROM laws 
                ORDER BY law_name
            """))
            old_laws = result.fetchall()
        
        # 표준 법률 데이터 로드
        standard_laws = self.load_standard_laws()
        
        # 매핑 딕셔너리 생성
        mapping = {}
        
        # 표준 법률명으로 인덱스 생성
        standard_index = {}
        for law in standard_laws:
            # 정식명칭으로 인덱싱
            law_name = law['law_name']
            short_name = law['law_short_name']
            
            standard_index[law_name] = law
            standard_index[short_name] = law
            
            # 띄어쓰기 제거한 버전도 추가
            normalized_name = law_name.replace(' ', '')
            standard_index[normalized_name] = law
        
        # 기존 법률명을 표준 법률명으로 매핑
        unmapped = []
        for old_law_name, old_short_name in old_laws:
            # 정확히 일치하는 경우
            if old_law_name in standard_index:
                mapping[old_law_name] = standard_index[old_law_name]
            # 띄어쓰기 제거 후 일치하는 경우
            elif old_law_name.replace(' ', '') in standard_index:
                mapping[old_law_name] = standard_index[old_law_name.replace(' ', '')]
            # 약칭으로 매칭
            elif old_short_name in standard_index:
                mapping[old_law_name] = standard_index[old_short_name]
            else:
                # 부분 매칭 시도
                found = False
                for std_name, std_law in standard_index.items():
                    if old_law_name in std_name or std_name in old_law_name:
                        mapping[old_law_name] = std_law
                        found = True
                        break
                
                if not found:
                    unmapped.append((old_law_name, old_short_name))
        
        logger.info(f"매핑 완료: {len(mapping)}개 법률 매핑됨")
        if unmapped:
            logger.warning(f"매핑 실패: {len(unmapped)}개 법률")
            for name, short in unmapped[:5]:  # 처음 5개만 출력
                logger.warning(f"  - {name} ({short})")
        
        return mapping
    
    def migrate_laws(self):
        """법률 데이터 마이그레이션 실행"""
        logger.info("법률 데이터 마이그레이션 시작...")
        
        # 표준 법률 데이터 로드
        standard_laws = self.load_standard_laws()
        
        # 새 세션 생성
        session = self.SessionLocal()
        
        try:
            # 표준 법률 데이터 입력
            for law_data in standard_laws:
                # 기존 법률 확인 (중복 방지)
                existing = session.query(LawV2).filter(
                    LawV2.law_name == law_data['law_name']
                ).first()
                
                if existing:
                    logger.debug(f"이미 존재: {law_data['law_name']}")
                    continue
                
                # 새 법률 생성
                new_law = LawV2(
                    law_name=law_data['law_name'],
                    law_short_name=law_data['law_short_name'],
                    law_type=law_data.get('law_type', '법률'),
                    law_category=self._categorize_law(law_data['law_name']),
                    effective_date=self._parse_date(law_data.get('effective_date')),
                    extra_metadata={
                        'law_no': law_data.get('law_no'),
                        'public_info': law_data.get('public_info'),
                        'link': law_data.get('link')
                    }
                )
                
                session.add(new_law)
                logger.info(f"추가: {law_data['law_name']} ({law_data['law_short_name']})")
            
            # 커밋
            session.commit()
            logger.info(f"법률 데이터 마이그레이션 완료: {len(standard_laws)}개 법률")
            
        except Exception as e:
            logger.error(f"마이그레이션 실패: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def _categorize_law(self, law_name: str) -> str:
        """법률명을 기반으로 카테고리 분류"""
        if '자본시장' in law_name:
            return '자본시장'
        elif '은행' in law_name:
            return '은행'
        elif '보험' in law_name:
            return '보험'
        elif '금융투자' in law_name:
            return '금융투자'
        elif '신용' in law_name or '대부' in law_name:
            return '여신전문'
        elif '회계' in law_name or '감사' in law_name:
            return '회계감사'
        elif '형법' in law_name or '처벌' in law_name:
            return '형사'
        elif '규정' in law_name or '세칙' in law_name:
            return '규정'
        else:
            return '기타'
    
    def _parse_date(self, date_str: str) -> datetime:
        """날짜 문자열 파싱"""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            return None
    
    def create_mapping_table(self):
        """기존 법률명과 새 법률 ID 매핑 테이블 생성"""
        logger.info("법률 매핑 테이블 생성 중...")
        
        mapping = self.create_law_mapping()
        
        # 매핑 테이블 생성
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS law_name_mapping (
                    old_law_name TEXT PRIMARY KEY,
                    new_law_id INTEGER,
                    new_law_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
        
        # 새 세션으로 법률 ID 조회 및 매핑 저장
        session = self.SessionLocal()
        
        try:
            for old_name, standard_law in mapping.items():
                # 새 DB에서 law_id 조회
                new_law = session.query(LawV2).filter(
                    LawV2.law_name == standard_law['law_name']
                ).first()
                
                if new_law:
                    with self.engine.connect() as conn:
                        conn.execute(text("""
                            INSERT OR REPLACE INTO law_name_mapping 
                            (old_law_name, new_law_id, new_law_name) 
                            VALUES (:old_name, :new_id, :new_name)
                        """), {
                            'old_name': old_name,
                            'new_id': new_law.law_id,
                            'new_name': new_law.law_name
                        })
                        conn.commit()
            
            logger.info("법률 매핑 테이블 생성 완료")
            
        finally:
            session.close()
    
    def verify_migration(self):
        """마이그레이션 검증"""
        logger.info("마이그레이션 검증 중...")
        
        session = self.SessionLocal()
        
        try:
            # 총 법률 수
            total_laws = session.query(LawV2).count()
            logger.info(f"총 법률 수: {total_laws}")
            
            # 법률 유형별 통계
            law_types = session.execute(text("""
                SELECT law_type, COUNT(*) as count 
                FROM laws_v2 
                GROUP BY law_type
            """)).fetchall()
            
            logger.info("법률 유형별 통계:")
            for law_type, count in law_types:
                logger.info(f"  - {law_type}: {count}개")
            
            # 카테고리별 통계
            categories = session.execute(text("""
                SELECT law_category, COUNT(*) as count 
                FROM laws_v2 
                GROUP BY law_category
                ORDER BY count DESC
            """)).fetchall()
            
            logger.info("카테고리별 통계:")
            for category, count in categories[:10]:  # 상위 10개
                logger.info(f"  - {category}: {count}개")
            
        finally:
            session.close()


def main():
    """메인 실행 함수"""
    logger.info("=== 법률 데이터 마이그레이션 시작 ===")
    
    migrator = LawMigrator()
    
    try:
        # 1. 테이블 생성
        migrator.create_tables()
        
        # 2. 법률 데이터 마이그레이션
        migrator.migrate_laws()
        
        # 3. 매핑 테이블 생성
        migrator.create_mapping_table()
        
        # 4. 검증
        migrator.verify_migration()
        
        logger.info("=== 법률 데이터 마이그레이션 완료 ===")
        
    except Exception as e:
        logger.error(f"마이그레이션 실패: {e}")
        raise


if __name__ == "__main__":
    main()