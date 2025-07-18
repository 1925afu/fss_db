-- FSS 규제 인텔리전스 플랫폼 데이터베이스 초기화 스크립트
-- PostgreSQL 전용

-- 한국어 collation 설정
CREATE COLLATION IF NOT EXISTS korean (provider = icu, locale = 'ko-KR');

-- 확장 기능 활성화 (필요시)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- 텍스트 검색 최적화용

-- 의결서 테이블 (복합 Primary Key)
CREATE TABLE IF NOT EXISTS decisions (
    decision_year INTEGER NOT NULL,
    decision_id INTEGER NOT NULL,
    decision_month INTEGER NOT NULL,
    decision_day INTEGER NOT NULL,
    agenda_no VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    category_1 VARCHAR(50) NOT NULL,
    category_2 VARCHAR(50) NOT NULL,
    submitter VARCHAR(100),
    submission_date DATE,
    stated_purpose TEXT,
    full_text TEXT,
    source_file VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extra_metadata JSONB,
    
    -- 복합 Primary Key
    PRIMARY KEY (decision_year, decision_id)
);

-- 조치 테이블
CREATE TABLE IF NOT EXISTS actions (
    action_id SERIAL PRIMARY KEY,
    decision_year INTEGER NOT NULL,
    decision_id INTEGER NOT NULL,
    entity_name VARCHAR(255) NOT NULL,
    industry_sector VARCHAR(50) NOT NULL,
    violation_details TEXT NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    fine_amount BIGINT,
    fine_basis_amount BIGINT,
    sanction_period VARCHAR(50),
    sanction_scope TEXT,
    effective_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extra_metadata JSONB,
    
    -- 복합 Foreign Key
    FOREIGN KEY (decision_year, decision_id) REFERENCES decisions(decision_year, decision_id)
);

-- 법규 테이블
CREATE TABLE IF NOT EXISTS laws (
    law_id SERIAL PRIMARY KEY,
    law_name VARCHAR(255) UNIQUE NOT NULL,
    law_short_name VARCHAR(100) NOT NULL,
    law_category VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extra_metadata JSONB
);

-- 조치-법규 매핑 테이블
CREATE TABLE IF NOT EXISTS action_law_map (
    map_id SERIAL PRIMARY KEY,
    action_id INTEGER NOT NULL REFERENCES actions(action_id),
    law_id INTEGER NOT NULL REFERENCES laws(law_id),
    article_details VARCHAR(100) NOT NULL,
    article_purpose TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    extra_metadata JSONB
);

-- 인덱스 생성 (성능 최적화용)
CREATE INDEX IF NOT EXISTS idx_decisions_date ON decisions(decision_year, decision_month, decision_day);
CREATE INDEX IF NOT EXISTS idx_decisions_category ON decisions(category_1, category_2);
CREATE INDEX IF NOT EXISTS idx_decisions_agenda ON decisions(agenda_no);
CREATE INDEX IF NOT EXISTS idx_decisions_fulltext ON decisions USING gin(to_tsvector('korean', full_text));

CREATE INDEX IF NOT EXISTS idx_actions_entity ON actions(entity_name);
CREATE INDEX IF NOT EXISTS idx_actions_industry ON actions(industry_sector);
CREATE INDEX IF NOT EXISTS idx_actions_type ON actions(action_type);
CREATE INDEX IF NOT EXISTS idx_actions_decision ON actions(decision_year, decision_id);

CREATE INDEX IF NOT EXISTS idx_laws_name ON laws(law_short_name);
CREATE INDEX IF NOT EXISTS idx_laws_category ON laws(law_category);

-- 트리거 함수: updated_at 자동 업데이트
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 트리거 생성
DROP TRIGGER IF EXISTS update_decisions_updated_at ON decisions;
CREATE TRIGGER update_decisions_updated_at
    BEFORE UPDATE ON decisions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_actions_updated_at ON actions;
CREATE TRIGGER update_actions_updated_at
    BEFORE UPDATE ON actions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_laws_updated_at ON laws;
CREATE TRIGGER update_laws_updated_at
    BEFORE UPDATE ON laws
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_action_law_map_updated_at ON action_law_map;
CREATE TRIGGER update_action_law_map_updated_at
    BEFORE UPDATE ON action_law_map
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 기본 법률 데이터 삽입 (주요 금융법)
INSERT INTO laws (law_name, law_short_name, law_category) VALUES
('은행법', '은행법', '은행'),
('보험업법', '보험업법', '보험'),
('자본시장과 금융투자업에 관한 법률', '자본시장법', '금융투자'),
('상호저축은행법', '상호저축은행법', '저축은행'),
('신용협동조합법', '신협법', '협동조합'),
('여신전문금융업법', '여신전문금융업법', '여신전문'),
('외국환거래법', '외환법', '외환'),
('금융실명거래 및 비밀보장에 관한 법률', '금융실명법', '금융일반'),
('전자금융거래법', '전자금융거래법', '전자금융'),
('공인회계사법', '공인회계사법', '회계감사'),
('주식회사 등의 외부감사에 관한 법률', '외부감사법', '회계감사')
ON CONFLICT (law_name) DO NOTHING;

-- 초기 설정 완료 로그
INSERT INTO laws (law_name, law_short_name, law_category) VALUES 
('_INIT_COMPLETE_', 'SYSTEM', 'SYSTEM')
ON CONFLICT (law_name) DO NOTHING;