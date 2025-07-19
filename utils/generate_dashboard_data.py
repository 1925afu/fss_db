#!/usr/bin/env python3
"""
대시보드용 통계 데이터를 생성하는 스크립트 (SQLAlchemy 버전)
PostgreSQL/SQLite 데이터베이스에서 데이터를 추출하여 JSON 형식으로 저장
"""

import json
import sys
import os
from datetime import datetime
from collections import defaultdict
from sqlalchemy import create_engine, func, case
from sqlalchemy.orm import sessionmaker

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.fsc_models import Decision, Action, Law, ActionLawMap
from app.core.config import settings

def generate_dashboard_data(output_path="./dashboard_data.json"):
    """데이터베이스에서 대시보드용 통계 데이터를 생성합니다."""
    
    # 데이터베이스 연결
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        dashboard_data = {
            "generated_at": datetime.now().isoformat(),
            "summary": {},
            "charts": {}
        }
        
        # 1. 전체 요약 통계
        total_decisions = db.query(Decision).count()
        total_actions = db.query(Action).count()
        total_laws = db.query(Law).count()
        total_fines = db.query(func.sum(Action.fine_amount)).filter(Action.fine_amount > 0).scalar() or 0
        
        dashboard_data["summary"] = {
            "total_decisions": total_decisions,
            "total_actions": total_actions,
            "total_laws": total_laws,
            "total_fines": total_fines,
            "total_fines_formatted": f"{total_fines:,.0f}원"
        }
        
        # 2. 월별 의결서 통계 - 연도별 월별 집계
        monthly_stats = db.query(
            Decision.decision_year,
            Decision.decision_month,
            Decision.decision_day,
            func.count('*').label('count')
        ).group_by(
            Decision.decision_year,
            Decision.decision_month,
            Decision.decision_day
        ).order_by(
            Decision.decision_year,
            Decision.decision_month
        ).all()
        
        monthly_labels = []
        monthly_data = []
        date_unknown_count = {}  # 연도별 날짜 미상 카운트
        
        for year, month, day, count in monthly_stats:
            if month == 1 and day == 1:  # 날짜 정보가 없는 경우
                if year not in date_unknown_count:
                    date_unknown_count[year] = 0
                date_unknown_count[year] += count
            elif month > 0:  # 유효한 월 데이터
                # 이미 추가된 연도-월인지 확인
                label = f"{year}년 {month}월"
                if label in monthly_labels:
                    idx = monthly_labels.index(label)
                    monthly_data[idx] += count
                else:
                    monthly_labels.append(label)
                    monthly_data.append(count)
        
        # 날짜 미상 데이터 추가
        for year, count in date_unknown_count.items():
            monthly_labels.append(f"{year}년 (날짜미상)")
            monthly_data.append(count)
        
        dashboard_data["charts"]["monthly_decisions"] = {
            "labels": monthly_labels,
            "data": monthly_data
        }
        
        # 3. 조치 유형별 통계
        action_types = db.query(
            Action.action_type,
            func.count('*').label('count')
        ).filter(
            Action.action_type.isnot(None)
        ).group_by(
            Action.action_type
        ).order_by(
            func.count('*').desc()
        ).limit(10).all()
        
        dashboard_data["charts"]["action_types"] = {
            "labels": [action_type or "기타" for action_type, _ in action_types],
            "data": [count for _, count in action_types]
        }
        
        # 4. 업권별 제재 통계
        sectors = db.query(
            Action.industry_sector,
            func.count('*').label('count')
        ).filter(
            Action.industry_sector.isnot(None)
        ).group_by(
            Action.industry_sector
        ).order_by(
            func.count('*').desc()
        ).limit(10).all()
        
        dashboard_data["charts"]["industry_sectors"] = {
            "labels": [sector for sector, _ in sectors],
            "data": [count for _, count in sectors]
        }
        
        # 5. 과태료 금액대별 분포
        fine_ranges = db.query(
            case(
                (Action.fine_amount == 0, '없음'),
                (Action.fine_amount < 10000000, '1천만원 미만'),
                (Action.fine_amount < 50000000, '5천만원 미만'),
                (Action.fine_amount < 100000000, '1억원 미만'),
                (Action.fine_amount < 500000000, '5억원 미만'),
                (Action.fine_amount < 1000000000, '10억원 미만'),
                else_='10억원 이상'
            ).label('range'),
            func.count('*').label('count')
        ).group_by('range').all()
        
        # 금액대별로 정렬
        range_order = ['없음', '1천만원 미만', '5천만원 미만', '1억원 미만', '5억원 미만', '10억원 미만', '10억원 이상']
        sorted_ranges = sorted(fine_ranges, key=lambda x: range_order.index(x[0]) if x[0] in range_order else 999)
        
        dashboard_data["charts"]["fine_ranges"] = {
            "labels": [range_name for range_name, _ in sorted_ranges if range_name != '없음'],
            "data": [count for range_name, count in sorted_ranges if range_name != '없음']
        }
        
        # 6. 상위 10개 과태료/과징금
        top_fines = db.query(
            Action.entity_name,
            Action.action_type,
            Action.fine_amount,
            Action.violation_details
        ).filter(
            Action.fine_amount > 0
        ).order_by(
            Action.fine_amount.desc()
        ).limit(10).all()
        
        dashboard_data["top_fines"] = [
            {
                "entity_name": entity,
                "action_type": action,
                "fine_amount": fine,
                "fine_amount_formatted": f"{fine:,.0f}원",
                "violation_summary": (violation[:100] + "...") if violation and len(violation) > 100 else (violation or "")
            }
            for entity, action, fine, violation in top_fines
        ]
        
        # 7. 법률별 인용 횟수 (상위 10개)
        law_citations = db.query(
            Law.law_short_name,
            func.count(ActionLawMap.law_id).label('citation_count')
        ).join(
            ActionLawMap, Law.law_id == ActionLawMap.law_id
        ).group_by(
            Law.law_id, Law.law_short_name
        ).order_by(
            func.count(ActionLawMap.law_id).desc()
        ).limit(10).all()
        
        dashboard_data["charts"]["law_citations"] = {
            "labels": [law for law, _ in law_citations],
            "data": [count for _, count in law_citations]
        }
        
        # 8. 최근 의결서 목록
        recent_decisions = db.query(
            Decision.decision_year,
            Decision.decision_id,
            Decision.decision_month,
            Decision.decision_day,
            Decision.title,
            Decision.category_1,
            Decision.category_2
        ).order_by(
            Decision.decision_year.desc(),
            Decision.decision_id.desc()
        ).limit(10).all()
        
        dashboard_data["recent_decisions"] = [
            {
                "decision_no": f"{year}-{id}호",
                "date": f"{year}년 {month}월 {day}일" if not (month == 1 and day == 1) else "날짜 정보 없음",
                "title": title,
                "category": f"{cat1}/{cat2}" if cat1 and cat2 else "미분류"
            }
            for year, id, month, day, title, cat1, cat2 in recent_decisions
        ]
        
        # 9. 복수 조치 통계 추가
        multiple_sanctions_count = 0
        total_individual_targets = 0
        
        for action in db.query(Action).all():
            if action.target_details and isinstance(action.target_details, dict):
                if action.target_details.get('type') == 'multiple_sanctions':
                    multiple_sanctions_count += 1
                    total_individual_targets += action.target_details.get('total_count', 0)
        
        dashboard_data["summary"]["multiple_sanctions_count"] = multiple_sanctions_count
        dashboard_data["summary"]["total_individual_targets"] = total_individual_targets
        
        # JSON 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
        
        print(f"대시보드 데이터가 생성되었습니다: {output_path}")
        print(f"- 총 의결서: {total_decisions}개")
        print(f"- 총 조치: {total_actions}개")
        print(f"- 복수 조치 의결서: {multiple_sanctions_count}개")
        print(f"- 총 과태료/과징금: {total_fines:,.0f}원")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    generate_dashboard_data()