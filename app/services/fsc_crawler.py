import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import os
import zipfile
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class FSCCrawler:
    """금융위원회 웹사이트 크롤러"""
    
    def __init__(self):
        self.base_url = settings.FSC_BASE_URL
        self.delay = settings.DOWNLOAD_DELAY
        self.max_retries = settings.MAX_RETRIES
        self.raw_zip_dir = settings.RAW_ZIP_DIR
        self.processed_pdf_dir = settings.PROCESSED_PDF_DIR
        
        # 디렉토리 생성
        os.makedirs(self.raw_zip_dir, exist_ok=True)
        os.makedirs(self.processed_pdf_dir, exist_ok=True)
        
        # 세션 생성
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search_decisions(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """지정된 기간의 의결서 목록을 검색합니다."""
        decisions = []
        
        # FSC 홈페이지의 실제 의결서 검색 URL
        search_url = f"{self.base_url}/no020101"
        
        # 검색 파라미터 (실제 FSC 게시판 구조에 맞게 수정)
        params = {
            'srchBeginDt': start_date.strftime('%Y-%m-%d'),
            'srchEndDt': end_date.strftime('%Y-%m-%d'),
            'srchKey': 'sj',  # 제목 검색
            'srchText': '의결서',  # 의결서 검색
            'curPage': 1
        }
        
        try:
            current_page = 1
            
            while True:
                params['curPage'] = current_page
                
                response = self.session.get(search_url, params=params)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # 실제 FSC 게시판 구조에 맞게 게시물 목록 파싱
                board_items = soup.select('div.board-list-wrap ul li')
                
                if not board_items:
                    break
                
                for item in board_items:
                    decision_info = self._parse_decision_item(item)
                    if decision_info and self._is_decision_document(decision_info):
                        decisions.append(decision_info)
                
                # 다음 페이지 확인 (실제 페이징 구조에 맞게 수정)
                next_page = soup.select_one('a.com.next')
                if not next_page or 'disabled' in next_page.get('class', []):
                    break
                
                current_page += 1
                time.sleep(self.delay)
                
        except Exception as e:
            logger.error(f"의결서 검색 중 오류 발생: {str(e)}")
            
        return decisions
    
    def _parse_decision_item(self, item) -> Optional[Dict]:
        """게시물 아이템을 파싱합니다."""
        try:
            # 실제 FSC 게시판 구조에 맞게 수정
            
            # 게시물 번호 추출
            count_element = item.select_one('div.count')
            post_no = count_element.get_text(strip=True) if count_element else ''
            
            # 제목과 링크 추출
            title_element = item.select_one('div.subject a')
            if not title_element:
                return None
            
            title = title_element.get_text(strip=True)
            link = title_element.get('href')
            
            # 날짜 추출
            date_element = item.select_one('div.day')
            date_str = date_element.get_text(strip=True) if date_element else ''
            
            # 첨부파일 목록 추출
            files = []
            file_elements = item.select('div.file-list')
            for file_elem in file_elements:
                file_name_elem = file_elem.select_one('span.name')
                download_link_elem = file_elem.select_one('span.ico.download a')
                
                if file_name_elem and download_link_elem:
                    files.append({
                        'name': file_name_elem.get_text(strip=True),
                        'url': download_link_elem.get('href')
                    })
            
            return {
                'title': title,
                'link': link,
                'date': date_str,
                'post_no': post_no,
                'files': files,
                'full_url': f"{self.base_url}{link}" if link.startswith('/') else link
            }
            
        except Exception as e:
            logger.error(f"게시물 파싱 중 오류 발생: {str(e)}")
            return None
    
    def _is_decision_document(self, decision_info: Dict) -> bool:
        """의결서 문서인지 판단합니다."""
        title = decision_info.get('title', '')
        files = decision_info.get('files', [])
        
        # 제목에 "의결서"가 포함되어 있는지 확인
        if '의결서' in title:
            return True
        
        # 파일 중에 의결서 ZIP 파일이 있는지 확인
        for file_info in files:
            file_name = file_info.get('name', '')
            if '의결서' in file_name and '.zip' in file_name:
                return True
        
        return False
    
    def download_decision_files(self, decisions: List[Dict]) -> List[str]:
        """의결서 파일들을 다운로드합니다."""
        downloaded_files = []
        
        for decision in decisions:
            try:
                # 게시물에서 직접 파일 다운로드 (상세 페이지 접근 불필요)
                files = self._download_files_from_decision(decision)
                downloaded_files.extend(files)
                
                time.sleep(self.delay)
                
            except Exception as e:
                logger.error(f"의결서 다운로드 중 오류 발생: {decision['title']} - {str(e)}")
                continue
        
        return downloaded_files
    
    def _download_files_from_decision(self, decision: Dict) -> List[str]:
        """의결서 정보에서 직접 파일을 다운로드합니다."""
        downloaded_files = []
        
        try:
            files = decision.get('files', [])
            
            for file_info in files:
                file_name = file_info.get('name', '')
                file_url = file_info.get('url', '')
                
                # 의결서 ZIP 파일 우선 다운로드
                if '의결서' in file_name and '.zip' in file_name:
                    full_url = f"{self.base_url}{file_url}" if file_url.startswith('/') else file_url
                    filename = self._download_file(full_url, decision['title'], file_name)
                    
                    if filename:
                        downloaded_files.append(filename)
                        
        except Exception as e:
            logger.error(f"파일 다운로드 중 오류 발생: {str(e)}")
            
        return downloaded_files
    
    def _download_file(self, url: str, decision_title: str, original_filename: str = None) -> Optional[str]:
        """파일을 다운로드합니다."""
        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            # 파일명 생성 (원본 파일명 우선 사용)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if original_filename:
                # 원본 파일명에서 확장자 추출
                name, ext = os.path.splitext(original_filename)
                safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                filename = f"{timestamp}_{safe_name[:50]}{ext}"
            else:
                # 의결서 제목으로 파일명 생성
                safe_title = "".join(c for c in decision_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                filename = f"{timestamp}_{safe_title[:50]}.zip"
            
            filepath = os.path.join(self.raw_zip_dir, filename)
            
            # 파일 저장
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"파일 다운로드 완료: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패: {url} - {str(e)}")
            return None
    
    def extract_zip_files(self) -> List[str]:
        """다운로드된 ZIP 파일들을 연도별로 분류하여 압축 해제합니다."""
        import re
        
        extracted_files = []
        
        # ZIP 파일 목록 확인
        zip_files = [f for f in os.listdir(self.raw_zip_dir) if f.endswith('.zip')]
        
        for zip_file in zip_files:
            zip_path = os.path.join(self.raw_zip_dir, zip_file)
            
            # ZIP 파일명에서 연도 추출
            year_match = re.search(r'(\d{4})년', zip_file)
            if not year_match:
                logger.warning(f"연도 추출 실패, 기본 폴더에 저장: {zip_file}")
                year_dir = self.processed_pdf_dir
            else:
                year = year_match.group(1)
                year_dir = os.path.join(self.processed_pdf_dir, year)
                os.makedirs(year_dir, exist_ok=True)
                logger.info(f"ZIP 파일 처리: {zip_file} -> {year}년 폴더")
            
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # ZIP 파일 내용 확인
                    file_list = zip_ref.namelist()
                    
                    # 의결서 PDF 파일만 추출
                    for file_name in file_list:
                        if file_name.endswith('.pdf') and '의결' in file_name:
                            # 임시 위치에 파일 추출
                            zip_ref.extract(file_name, year_dir)
                            
                            # 파일명 정리
                            original_path = os.path.join(year_dir, file_name)
                            new_name = os.path.basename(file_name)
                            new_path = os.path.join(year_dir, new_name)
                            
                            if original_path != new_path:
                                # 중간 디렉토리가 있는 경우 파일을 이동
                                if os.path.dirname(file_name):
                                    os.rename(original_path, new_path)
                                    # 빈 디렉토리 정리
                                    try:
                                        os.rmdir(os.path.dirname(original_path))
                                    except OSError:
                                        pass  # 디렉토리가 비어있지 않으면 무시
                            
                            extracted_files.append(f"{year if year_match else 'default'}/{new_name}")
                            logger.info(f"PDF 파일 추출 완료: {year if year_match else 'default'}/{new_name}")
                
            except Exception as e:
                logger.error(f"ZIP 파일 압축 해제 실패: {zip_file} - {str(e)}")
                continue
        
        return extracted_files
    
    def crawl_decisions(self, start_date: datetime, end_date: datetime) -> Dict[str, List[str]]:
        """의결서 크롤링 전체 프로세스를 실행합니다."""
        logger.info(f"의결서 크롤링 시작: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        
        # 1. 의결서 목록 검색
        decisions = self.search_decisions(start_date, end_date)
        logger.info(f"검색된 의결서 수: {len(decisions)}")
        
        # 2. 파일 다운로드
        downloaded_files = self.download_decision_files(decisions)
        logger.info(f"다운로드된 파일 수: {len(downloaded_files)}")
        
        # 3. ZIP 파일 압축 해제
        extracted_files = self.extract_zip_files()
        logger.info(f"추출된 PDF 파일 수: {len(extracted_files)}")
        
        return {
            'decisions': decisions,
            'downloaded_files': downloaded_files,
            'extracted_files': extracted_files
        }