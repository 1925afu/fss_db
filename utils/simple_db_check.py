#!/usr/bin/env python3
"""
SQLite 데이터베이스 간단 확인 스크립트
Python 내장 모듈만 사용하여 데이터베이스 내용을 확인합니다.
"""

import sqlite3
import os
from datetime import datetime

def format_table(headers, rows, max_width=30):
    """간단한 테이블 포맷터"""
    # 각 컬럼의 최대 너비 계산
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            cell_str = str(cell) if cell is not None else 'NULL'
            # 긴 텍스트는 잘라내기
            if len(cell_str) > max_width:
                cell_str = cell_str[:max_width-3] + '...'
            col_widths[i] = max(col_widths[i], len(cell_str))
    
    # 테이블 출력
    separator = '+-' + '-+-'.join('-' * w for w in col_widths) + '-+'
    print(separator)
    
    # 헤더 출력
    print('| ' + ' | '.join(str(h).ljust(w) for h, w in zip(headers, col_widths)) + ' |')
    print(separator)
    
    # 데이터 출력
    for row in rows:
        formatted_row = []
        for i, cell in enumerate(row):
            cell_str = str(cell) if cell is not None else 'NULL'
            # 긴 텍스트는 잘라내기
            if len(cell_str) > max_width:
                cell_str = cell_str[:max_width-3] + '...'
            formatted_row.append(cell_str.ljust(col_widths[i]))
        print('| ' + ' | '.join(formatted_row) + ' |')
    
    print(separator)

def check_database(db_path="./fss_db.sqlite"):
    """데이터베이스 내용을 간단히 확인합니다."""
    
    # 파일 존재 확인
    if not os.path.exists(db_path):
        print(f"오류: 데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("="*70)
        print(f"SQLite 데이터베이스 확인: {db_path}")
        print(f"확인 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # 파일 크기
        file_size = os.path.getsize(db_path)
        print(f"\n파일 크기: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        
        # 테이블 목록 조회
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        if not tables:
            print("\n데이터베이스에 테이블이 없습니다.")
            return
        
        print(f"\n발견된 테이블: {len(tables)}개")
        print("-"*50)
        
        # 전체 요약
        print("\n[테이블별 레코드 수]")
        summary_data = []
        for (table_name,) in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            summary_data.append([table_name, f"{count:,}"])
        
        format_table(['테이블명', '레코드 수'], summary_data)
        
        # 각 테이블 상세 정보
        for (table_name,) in tables:
            print(f"\n\n{'='*70}")
            print(f"테이블: {table_name}")
            print("="*70)
            
            # 컬럼 정보
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("\n[컬럼 구조]")
            column_data = []
            column_names = []
            for col in columns:
                column_data.append([col[1], col[2], 'YES' if col[3] else 'NO', 'PK' if col[5] else ''])
                column_names.append(col[1])
            
            format_table(['컬럼명', '타입', 'NOT NULL', 'KEY'], column_data)
            
            # 레코드 수
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"\n총 레코드 수: {count:,}개")
            
            # 샘플 데이터
            if count > 0:
                print(f"\n[샘플 데이터] (최대 5개)")
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                sample_rows = cursor.fetchall()
                
                format_table(column_names, sample_rows)
                
                # 특정 테이블의 추가 통계
                if table_name == 'decisions':
                    print("\n[연도별 의결서 수]")
                    cursor.execute("""
                        SELECT decision_year, COUNT(*) as count
                        FROM decisions
                        GROUP BY decision_year
                        ORDER BY decision_year DESC
                        LIMIT 10
                    """)
                    year_stats = cursor.fetchall()
                    if year_stats:
                        format_table(['연도', '건수'], year_stats)
                    
                    print("\n[카테고리별 통계] (상위 10개)")
                    cursor.execute("""
                        SELECT category_1, category_2, COUNT(*) as count
                        FROM decisions
                        WHERE category_1 IS NOT NULL
                        GROUP BY category_1, category_2
                        ORDER BY count DESC
                        LIMIT 10
                    """)
                    category_stats = cursor.fetchall()
                    if category_stats:
                        format_table(['카테고리1', '카테고리2', '건수'], category_stats)
                
                elif table_name == 'actions':
                    print("\n[조치 유형별 통계] (상위 10개)")
                    cursor.execute("""
                        SELECT action_type, COUNT(*) as count
                        FROM actions
                        WHERE action_type IS NOT NULL
                        GROUP BY action_type
                        ORDER BY count DESC
                        LIMIT 10
                    """)
                    action_stats = cursor.fetchall()
                    if action_stats:
                        format_table(['조치 유형', '건수'], action_stats)
                    
                    print("\n[과태료/과징금 통계]")
                    cursor.execute("""
                        SELECT 
                            COUNT(CASE WHEN fine_amount > 0 THEN 1 END) as fine_count,
                            SUM(fine_amount) as total_fine,
                            AVG(CASE WHEN fine_amount > 0 THEN fine_amount END) as avg_fine,
                            MAX(fine_amount) as max_fine
                        FROM actions
                    """)
                    fine_stats = cursor.fetchone()
                    if fine_stats:
                        print(f"  - 과태료 부과 건수: {fine_stats[0]:,}건")
                        print(f"  - 총 과태료: {fine_stats[1]:,.0f}원" if fine_stats[1] else "  - 총 과태료: 0원")
                        print(f"  - 평균 과태료: {fine_stats[2]:,.0f}원" if fine_stats[2] else "  - 평균 과태료: 0원")
                        print(f"  - 최고 과태료: {fine_stats[3]:,.0f}원" if fine_stats[3] else "  - 최고 과태료: 0원")
        
        print("\n" + "="*70)
        print("데이터베이스 확인 완료")
        print("="*70)
        
    except sqlite3.Error as e:
        print(f"\n데이터베이스 오류: {e}")
    except Exception as e:
        print(f"\n오류 발생: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_database()