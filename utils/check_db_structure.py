#!/usr/bin/env python3
"""데이터베이스 구조 간단히 확인"""

import sqlite3

conn = sqlite3.connect('fss_db.sqlite')
cursor = conn.cursor()

# 테이블 목록 확인
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = cursor.fetchall()
print("테이블 목록:")
for table in tables:
    print(f"  - {table[0]}")

# decisions 테이블 구조 확인
print("\ndecisions 테이블 컬럼:")
cursor.execute("PRAGMA table_info(decisions)")
columns = cursor.fetchall()
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

# actions 테이블 구조 확인
print("\nactions 테이블 컬럼:")
cursor.execute("PRAGMA table_info(actions)")
columns = cursor.fetchall()
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

conn.close()