#!/usr/bin/env python3
"""
데이터베이스 검사 스크립트
모든 테이블의 구조와 데이터를 조회하여 표시합니다.
"""

import sqlite3
import pandas as pd
from tabulate import tabulate
from datetime import datetime

def inspect_database(db_path="./fss_db.sqlite"):
    """데이터베이스를 검사하고 모든 테이블의 정보를 출력합니다."""
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"\n{'='*80}")
        print(f"데이터베이스 검사: {db_path}")
        print(f"검사 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        # 모든 테이블 목록 조회
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        
        if not tables:
            print("데이터베이스에 테이블이 없습니다.")
            return
        
        print(f"발견된 테이블 수: {len(tables)}\n")
        
        # 각 테이블에 대한 상세 정보
        for table_name in tables:
            table_name = table_name[0]
            print(f"\n{'='*80}")
            print(f"테이블: {table_name}")
            print(f"{'='*80}")
            
            # 테이블 스키마 정보
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("\n[테이블 구조]")
            schema_data = []
            for col in columns:
                schema_data.append({
                    '컬럼명': col[1],
                    '데이터타입': col[2],
                    'NULL 허용': 'NO' if col[3] else 'YES',
                    '기본값': col[4] if col[4] else '',
                    'PK': 'YES' if col[5] else 'NO'
                })
            
            print(tabulate(schema_data, headers='keys', tablefmt='grid'))
            
            # 레코드 수 조회
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"\n[레코드 수]: {count:,} 건")
            
            # 샘플 데이터 조회
            if count > 0:
                print(f"\n[샘플 데이터] (최대 5건)")
                
                # pandas를 사용하여 데이터 조회 및 포맷팅
                df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 5", conn)
                
                # 긴 텍스트 필드 축약
                for col in df.columns:
                    if df[col].dtype == 'object':
                        df[col] = df[col].apply(lambda x: str(x)[:50] + '...' if x and len(str(x)) > 50 else x)
                
                print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
                
                # 특정 테이블에 대한 추가 통계
                if table_name == 'decisions':
                    print("\n[의결서 통계]")
                    
                    # 연도별 의결서 수
                    year_stats = pd.read_sql_query("""
                        SELECT decision_year, COUNT(*) as count
                        FROM decisions
                        GROUP BY decision_year
                        ORDER BY decision_year DESC
                    """, conn)
                    print("\n연도별 의결서 수:")
                    print(tabulate(year_stats, headers='keys', tablefmt='grid', showindex=False))
                    
                    # 카테고리별 통계
                    category_stats = pd.read_sql_query("""
                        SELECT category_1, category_2, COUNT(*) as count
                        FROM decisions
                        GROUP BY category_1, category_2
                        ORDER BY count DESC
                        LIMIT 10
                    """, conn)
                    print("\n상위 10개 카테고리:")
                    print(tabulate(category_stats, headers='keys', tablefmt='grid', showindex=False))
                
                elif table_name == 'actions':
                    print("\n[조치 통계]")
                    
                    # 조치 유형별 통계
                    action_stats = pd.read_sql_query("""
                        SELECT action_type, COUNT(*) as count
                        FROM actions
                        GROUP BY action_type
                        ORDER BY count DESC
                        LIMIT 10
                    """, conn)
                    print("\n조치 유형별 통계:")
                    print(tabulate(action_stats, headers='keys', tablefmt='grid', showindex=False))
                    
                    # 업권별 통계
                    sector_stats = pd.read_sql_query("""
                        SELECT industry_sector, COUNT(*) as count
                        FROM actions
                        GROUP BY industry_sector
                        ORDER BY count DESC
                        LIMIT 10
                    """, conn)
                    print("\n업권별 통계:")
                    print(tabulate(sector_stats, headers='keys', tablefmt='grid', showindex=False))
                    
                    # 과태료/과징금 통계
                    fine_stats = pd.read_sql_query("""
                        SELECT 
                            COUNT(CASE WHEN fine_amount > 0 THEN 1 END) as fine_count,
                            SUM(fine_amount) as total_fine,
                            AVG(CASE WHEN fine_amount > 0 THEN fine_amount END) as avg_fine,
                            MAX(fine_amount) as max_fine
                        FROM actions
                    """, conn)
                    print("\n과태료/과징금 통계:")
                    print(tabulate(fine_stats, headers='keys', tablefmt='grid', showindex=False))
                
                elif table_name == 'laws':
                    print("\n[법규 통계]")
                    
                    # 법규 카테고리별 통계
                    law_category_stats = pd.read_sql_query("""
                        SELECT law_category, COUNT(*) as count
                        FROM laws
                        GROUP BY law_category
                        ORDER BY count DESC
                    """, conn)
                    print("\n법규 카테고리별 통계:")
                    print(tabulate(law_category_stats, headers='keys', tablefmt='grid', showindex=False))
        
        # 전체 데이터베이스 통계
        print(f"\n{'='*80}")
        print("전체 데이터베이스 요약")
        print(f"{'='*80}")
        
        total_stats = []
        for table_name in tables:
            table_name = table_name[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            total_stats.append({
                '테이블명': table_name,
                '레코드 수': f"{count:,}"
            })
        
        print(tabulate(total_stats, headers='keys', tablefmt='grid'))
        
        # 데이터베이스 파일 크기
        import os
        if os.path.exists(db_path):
            size_mb = os.path.getsize(db_path) / (1024 * 1024)
            print(f"\n데이터베이스 파일 크기: {size_mb:.2f} MB")
        
    except sqlite3.Error as e:
        print(f"데이터베이스 오류: {e}")
    except Exception as e:
        print(f"일반 오류: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    inspect_database()