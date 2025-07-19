#!/usr/bin/env python3
"""
데이터베이스 NULL 값 분석 스크립트
각 테이블의 NULL 값 현황을 상세히 분석합니다.
"""

import sqlite3
import os
from datetime import datetime

def analyze_null_values(db_path="./fss_db.sqlite"):
    """데이터베이스의 NULL 값 현황을 분석합니다."""
    
    if not os.path.exists(db_path):
        print(f"오류: 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("="*80)
        print(f"데이터베이스 NULL 값 분석")
        print(f"분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # 테이블 목록 조회
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        # 전체 요약 데이터 수집
        summary_data = []
        
        for (table_name,) in tables:
            print(f"\n\n{'='*80}")
            print(f"테이블: {table_name}")
            print("="*80)
            
            # 전체 레코드 수
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = cursor.fetchone()[0]
            print(f"\n총 레코드 수: {total_rows:,}개")
            
            if total_rows == 0:
                print("데이터가 없습니다.")
                continue
            
            # 컬럼 정보 가져오기
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("\n[컬럼별 NULL 값 분석]")
            print("-"*80)
            print(f"{'컬럼명':<30} {'데이터타입':<15} {'NULL 개수':>10} {'NULL 비율':>10} {'상태':<10}")
            print("-"*80)
            
            table_null_count = 0
            
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                
                # NULL 값 개수 계산
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col_name} IS NULL")
                null_count = cursor.fetchone()[0]
                null_ratio = (null_count / total_rows) * 100
                
                table_null_count += null_count
                
                # 상태 판단
                if null_ratio == 0:
                    status = "✓ 완전"
                elif null_ratio < 10:
                    status = "○ 양호"
                elif null_ratio < 50:
                    status = "△ 주의"
                else:
                    status = "✗ 심각"
                
                print(f"{col_name:<30} {col_type:<15} {null_count:>10,} {null_ratio:>9.1f}% {status:<10}")
                
                # 주요 컬럼의 상세 분석
                if null_count > 0 and col_name in ['category_1', 'category_2', 'violation_details', 'action_reason']:
                    analyze_null_patterns(cursor, table_name, col_name, total_rows)
            
            print("-"*80)
            
            # 테이블 요약
            summary_data.append({
                'table': table_name,
                'total_rows': total_rows,
                'total_nulls': table_null_count,
                'avg_null_ratio': (table_null_count / (total_rows * len(columns))) * 100
            })
            
            # 특정 테이블의 추가 분석
            if table_name == 'decisions':
                analyze_decisions_nulls(cursor, total_rows)
            elif table_name == 'actions':
                analyze_actions_nulls(cursor, total_rows)
        
        # 전체 요약
        print("\n\n" + "="*80)
        print("전체 데이터베이스 NULL 값 요약")
        print("="*80)
        
        for summary in summary_data:
            print(f"\n{summary['table']} 테이블:")
            print(f"  - 전체 레코드: {summary['total_rows']:,}개")
            print(f"  - NULL 값 총계: {summary['total_nulls']:,}개")
            print(f"  - 평균 NULL 비율: {summary['avg_null_ratio']:.1f}%")
        
        # 개선 방안 제시
        print("\n\n" + "="*80)
        print("데이터 품질 개선 방안")
        print("="*80)
        print_improvement_suggestions(cursor)
        
    except sqlite3.Error as e:
        print(f"\n데이터베이스 오류: {e}")
    except Exception as e:
        print(f"\n오류 발생: {e}")
    finally:
        if conn:
            conn.close()

def analyze_null_patterns(cursor, table_name, col_name, total_rows):
    """특정 컬럼의 NULL 패턴을 분석합니다."""
    print(f"\n  [{col_name} NULL 패턴 분석]")
    
    # NULL이 아닌 값들의 분포 확인
    cursor.execute(f"""
        SELECT {col_name}, COUNT(*) as count
        FROM {table_name}
        WHERE {col_name} IS NOT NULL
        GROUP BY {col_name}
        ORDER BY count DESC
        LIMIT 5
    """)
    non_null_values = cursor.fetchall()
    
    if non_null_values:
        print("  NULL이 아닌 값들의 분포 (상위 5개):")
        for value, count in non_null_values:
            print(f"    - {value}: {count}건")

def analyze_decisions_nulls(cursor, total_rows):
    """decisions 테이블의 NULL 패턴을 상세 분석합니다."""
    print("\n[decisions 테이블 NULL 패턴 상세 분석]")
    
    # category가 NULL인 레코드들의 연도 분포
    cursor.execute("""
        SELECT decision_year, COUNT(*) as count
        FROM decisions
        WHERE category_1 IS NULL OR category_2 IS NULL
        GROUP BY decision_year
        ORDER BY decision_year DESC
    """)
    year_nulls = cursor.fetchall()
    
    if year_nulls:
        print("\n카테고리가 NULL인 의결서의 연도별 분포:")
        for year, count in year_nulls:
            print(f"  - {year}년: {count}건")
    
    # 제목에 특정 패턴이 있는지 확인
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM decisions
        WHERE category_1 IS NULL 
        AND (title LIKE '%과태료%' OR title LIKE '%과징금%' OR title LIKE '%경고%')
    """)
    pattern_count = cursor.fetchone()[0]
    
    if pattern_count > 0:
        print(f"\n카테고리가 NULL이지만 제목에 제재 관련 키워드가 있는 경우: {pattern_count}건")

def analyze_actions_nulls(cursor, total_rows):
    """actions 테이블의 NULL 패턴을 상세 분석합니다."""
    print("\n[actions 테이블 NULL 패턴 상세 분석]")
    
    # violation_details가 NULL인 레코드들의 action_type 분포
    cursor.execute("""
        SELECT action_type, COUNT(*) as count
        FROM actions
        WHERE violation_details IS NULL
        GROUP BY action_type
        ORDER BY count DESC
        LIMIT 5
    """)
    type_nulls = cursor.fetchall()
    
    if type_nulls:
        print("\nviolation_details가 NULL인 레코드의 조치 유형별 분포:")
        for action_type, count in type_nulls:
            print(f"  - {action_type}: {count}건")
    
    # 금액이 있지만 상세내용이 없는 경우
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM actions
        WHERE violation_details IS NULL 
        AND fine_amount > 0
    """)
    fine_no_details = cursor.fetchone()[0]
    
    if fine_no_details > 0:
        print(f"\n과태료/과징금이 있지만 위반상세가 NULL인 경우: {fine_no_details}건")

def print_improvement_suggestions(cursor):
    """데이터 품질 개선 방안을 제시합니다."""
    
    # decisions 테이블 카테고리 NULL 확인
    cursor.execute("""
        SELECT COUNT(*) FROM decisions 
        WHERE category_1 IS NULL OR category_2 IS NULL
    """)
    category_nulls = cursor.fetchone()[0]
    
    # actions 테이블 violation_details NULL 확인
    cursor.execute("""
        SELECT COUNT(*) FROM actions 
        WHERE violation_details IS NULL
    """)
    violation_nulls = cursor.fetchone()[0]
    
    print("\n1. 주요 개선 필요 사항:")
    
    if category_nulls > 0:
        print(f"\n   • decisions 테이블의 카테고리 분류 ({category_nulls}건)")
        print("     - 제목과 내용을 기반으로 자동 분류 알고리즘 적용 필요")
        print("     - AI 기반 텍스트 분류 모델 활용 권장")
    
    if violation_nulls > 0:
        print(f"\n   • actions 테이블의 위반상세 내용 ({violation_nulls}건)")
        print("     - PDF 원문에서 위반 내용 추출 로직 개선 필요")
        print("     - 정규식 패턴 확장 또는 AI 추출 강화")
    
    print("\n2. 데이터 보완 방안:")
    print("   • 규칙 기반 추출기(rule_based_extractor.py) 패턴 개선")
    print("   • Gemini API를 활용한 재처리")
    print("   • 수동 검토 및 라벨링을 통한 학습 데이터 구축")
    
    print("\n3. 향후 데이터 수집 시 고려사항:")
    print("   • 필수 필드 검증 로직 강화")
    print("   • 데이터 입력 시 유효성 검사 추가")
    print("   • 정기적인 데이터 품질 모니터링 체계 구축")

if __name__ == "__main__":
    analyze_null_values()