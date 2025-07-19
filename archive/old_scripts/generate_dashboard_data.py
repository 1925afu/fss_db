#!/usr/bin/env python3
"""
대시보드용 통계 데이터를 생성하는 스크립트
SQLite 데이터베이스에서 데이터를 추출하여 JSON 형식으로 저장
"""

import sqlite3
import json
from datetime import datetime
from collections import defaultdict

def generate_dashboard_data(db_path="./fss_db.sqlite", output_path="./dashboard_data.json"):
    """데이터베이스에서 대시보드용 통계 데이터를 생성합니다."""
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        dashboard_data = {
            "generated_at": datetime.now().isoformat(),
            "summary": {},
            "charts": {}
        }
        
        # 1. 전체 요약 통계
        cursor.execute("SELECT COUNT(*) FROM decisions")
        total_decisions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM actions")
        total_actions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM laws")
        total_laws = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(fine_amount) FROM actions WHERE fine_amount > 0")
        total_fines = cursor.fetchone()[0] or 0
        
        dashboard_data["summary"] = {
            "total_decisions": total_decisions,
            "total_actions": total_actions,
            "total_laws": total_laws,
            "total_fines": total_fines,
            "total_fines_formatted": f"{total_fines:,.0f}원"
        }
        
        # 2. 일별 의결서 수 (2025년 1월)
        cursor.execute("""
            SELECT decision_day, COUNT(*) as count
            FROM decisions
            WHERE decision_year = 2025 AND decision_month = 1
            GROUP BY decision_day
            ORDER BY decision_day
        """)
        daily_decisions = cursor.fetchall()
        
        dashboard_data["charts"]["daily_decisions"] = {
            "labels": [f"1월 {day}일" for day, _ in daily_decisions],
            "data": [count for _, count in daily_decisions]
        }
        
        # 3. 카테고리별 분포
        cursor.execute("""
            SELECT category_1, category_2, COUNT(*) as count
            FROM decisions
            WHERE category_1 IS NOT NULL AND category_1 != ''
            GROUP BY category_1, category_2
            ORDER BY count DESC
        """)
        categories = cursor.fetchall()
        
        # 카테고리1별 집계
        cat1_counts = defaultdict(int)
        for cat1, cat2, count in categories:
            cat1_counts[cat1] += count
        
        dashboard_data["charts"]["category_distribution"] = {
            "labels": list(cat1_counts.keys()),
            "data": list(cat1_counts.values())
        }
        
        # 4. 조치 유형별 통계
        cursor.execute("""
            SELECT action_type, COUNT(*) as count
            FROM actions
            WHERE action_type IS NOT NULL
            GROUP BY action_type
            ORDER BY count DESC
            LIMIT 10
        """)
        action_types = cursor.fetchall()
        
        dashboard_data["charts"]["action_types"] = {
            "labels": [action for action, _ in action_types],
            "data": [count for _, count in action_types]
        }
        
        # 5. 업권별 제재 통계
        cursor.execute("""
            SELECT industry_sector, COUNT(*) as count
            FROM actions
            WHERE industry_sector IS NOT NULL
            GROUP BY industry_sector
            ORDER BY count DESC
            LIMIT 10
        """)
        sectors = cursor.fetchall()
        
        dashboard_data["charts"]["industry_sectors"] = {
            "labels": [sector for sector, _ in sectors],
            "data": [count for _, count in sectors]
        }
        
        # 6. 과태료 금액대별 분포
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN fine_amount = 0 THEN '없음'
                    WHEN fine_amount < 10000000 THEN '1천만원 미만'
                    WHEN fine_amount < 50000000 THEN '5천만원 미만'
                    WHEN fine_amount < 100000000 THEN '1억원 미만'
                    WHEN fine_amount < 500000000 THEN '5억원 미만'
                    WHEN fine_amount < 1000000000 THEN '10억원 미만'
                    ELSE '10억원 이상'
                END as range,
                COUNT(*) as count
            FROM actions
            GROUP BY range
            ORDER BY 
                CASE range
                    WHEN '없음' THEN 0
                    WHEN '1천만원 미만' THEN 1
                    WHEN '5천만원 미만' THEN 2
                    WHEN '1억원 미만' THEN 3
                    WHEN '5억원 미만' THEN 4
                    WHEN '10억원 미만' THEN 5
                    ELSE 6
                END
        """)
        fine_ranges = cursor.fetchall()
        
        dashboard_data["charts"]["fine_ranges"] = {
            "labels": [range_name for range_name, _ in fine_ranges],
            "data": [count for _, count in fine_ranges]
        }
        
        # 7. 상위 10개 과태료/과징금
        cursor.execute("""
            SELECT 
                entity_name,
                action_type,
                fine_amount,
                violation_details
            FROM actions
            WHERE fine_amount > 0
            ORDER BY fine_amount DESC
            LIMIT 10
        """)
        top_fines = cursor.fetchall()
        
        dashboard_data["top_fines"] = [
            {
                "entity_name": entity,
                "action_type": action,
                "fine_amount": fine,
                "fine_amount_formatted": f"{fine:,.0f}원",
                "violation_summary": violation[:100] + "..." if len(violation) > 100 else violation
            }
            for entity, action, fine, violation in top_fines
        ]
        
        # 8. 법률별 인용 횟수 (상위 10개)
        cursor.execute("""
            SELECT l.law_short_name, COUNT(alm.law_id) as citation_count
            FROM laws l
            JOIN action_law_map alm ON l.law_id = alm.law_id
            GROUP BY l.law_id, l.law_short_name
            ORDER BY citation_count DESC
            LIMIT 10
        """)
        law_citations = cursor.fetchall()
        
        dashboard_data["charts"]["law_citations"] = {
            "labels": [law for law, _ in law_citations],
            "data": [count for _, count in law_citations]
        }
        
        # 9. 최근 의결서 목록
        cursor.execute("""
            SELECT 
                decision_year,
                decision_id,
                decision_month,
                decision_day,
                title,
                category_1,
                category_2
            FROM decisions
            ORDER BY decision_year DESC, decision_id DESC
            LIMIT 10
        """)
        recent_decisions = cursor.fetchall()
        
        dashboard_data["recent_decisions"] = [
            {
                "decision_no": f"{year}-{id}호",
                "date": f"{year}년 {month}월 {day}일" if month > 0 else "날짜 정보 없음",
                "title": title,
                "category": f"{cat1}/{cat2}" if cat1 and cat2 else "미분류"
            }
            for year, id, month, day, title, cat1, cat2 in recent_decisions
        ]
        
        # JSON 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
        
        print(f"대시보드 데이터가 생성되었습니다: {output_path}")
        print(f"- 총 의결서: {total_decisions}개")
        print(f"- 총 조치: {total_actions}개")
        print(f"- 총 과태료/과징금: {total_fines:,.0f}원")
        
    except sqlite3.Error as e:
        print(f"데이터베이스 오류: {e}")
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    generate_dashboard_data()