#!/usr/bin/env python3
"""대시보드 HTML 파일 업데이트"""
import json
import re

# dashboard_data.json 읽기
with open('dashboard_data.json', 'r', encoding='utf-8') as f:
    new_data = json.load(f)

# dashboard_v3.html 읽기
with open('dashboard_v3.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# dashboardData 객체 찾기 및 교체
pattern = r'const dashboardData = \{[\s\S]*?\n\s*\};'
replacement = f'const dashboardData = {json.dumps(new_data, ensure_ascii=False, indent=8)};'

# 교체
updated_html = re.sub(pattern, replacement, html_content)

# 파일 저장
with open('dashboard_v3.html', 'w', encoding='utf-8') as f:
    f.write(updated_html)

print("dashboard_v3.html이 업데이트되었습니다.")
print(f"- 총 의결서: {new_data['summary']['total_decisions']}")
print(f"- 총 조치: {new_data['summary']['total_actions']}")
print(f"- 복수 조치: {new_data['summary']['multiple_sanctions_count']}")
print(f"- 총 과태료/과징금: {new_data['summary']['total_fines_formatted']}")