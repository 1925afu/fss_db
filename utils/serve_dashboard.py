#!/usr/bin/env python3
"""
대시보드를 위한 간단한 웹 서버
CORS 문제를 해결하기 위해 로컬 웹 서버를 실행합니다.
"""

import http.server
import socketserver
import os
import webbrowser
from threading import Timer

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def open_browser():
    """1초 후 브라우저를 자동으로 엽니다."""
    webbrowser.open(f'http://localhost:{PORT}/dashboard.html')

if __name__ == '__main__':
    # 현재 디렉토리로 변경
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"대시보드 서버가 시작되었습니다!")
        print(f"브라우저에서 다음 주소로 접속하세요: http://localhost:{PORT}/dashboard.html")
        print("종료하려면 Ctrl+C를 누르세요.")
        
        # 1초 후 자동으로 브라우저 열기
        Timer(1, open_browser).start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n서버를 종료합니다.")
            httpd.shutdown()