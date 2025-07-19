#!/usr/bin/env python3
"""
매칭되는 의결 파일이 없는 의결서들의 날짜를 NULL로 업데이트
"""

import sqlite3

def update_unmatched_dates():
    """1월 1일로 남아있는 의결서들의 날짜를 NULL로 업데이트"""
    
    conn = sqlite3.connect('./fss_db.sqlite')
    cursor = conn.cursor()
    
    # 1월 1일인 의결서들의 날짜를 0으로 업데이트 (날짜 정보 없음을 의미)
    cursor.execute("""
        UPDATE decisions 
        SET decision_month = 0, decision_day = 0
        WHERE decision_month = 1 AND decision_day = 1
    """)
    
    updated_count = cursor.rowcount
    conn.commit()
    
    print(f"{updated_count}개 의결서의 날짜를 NULL로 업데이트했습니다.")
    
    # 업데이트 후 확인
    cursor.execute("""
        SELECT 
            CASE 
                WHEN decision_month = 0 THEN '날짜 정보 없음'
                ELSE decision_month || '월 ' || decision_day || '일'
            END as date_info,
            COUNT(*) as count
        FROM decisions
        WHERE decision_year = 2025
        GROUP BY decision_month, decision_day
        ORDER BY decision_month, decision_day
    """)
    
    print("\n=== 업데이트 후 날짜별 분포 ===")
    for row in cursor.fetchall():
        print(f"{row[0]}: {row[1]}건")
    
    conn.close()

if __name__ == "__main__":
    update_unmatched_dates()