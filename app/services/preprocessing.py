"""
PDF 전처리 모듈
PDF 파일에서 Gemini가 잘 이해할 수 있는 고품질 텍스트를 추출하고 정제
"""
import re
import logging
from typing import Optional, List, Tuple
import PyPDF2
import os

logger = logging.getLogger(__name__)


class PDFPreprocessor:
    """PDF 전처리 서비스"""
    
    def __init__(self):
        # 제거할 패턴들
        self.header_patterns = [
            r'금융위원회\s*\d{4}-\d+호',
            r'의\s*결\s*서',
            r'금\s*융\s*위\s*원\s*회',
            r'Financial Services Commission',
            r'페이지\s*\d+\s*/\s*\d+',
            r'- \d+ -',
        ]
        
        # 테이블 감지 패턴
        self.table_patterns = [
            r'[│├┤┌┐└┘─┼]',  # 테이블 문자
            r'\s{2,}\|\s{2,}',  # 파이프로 구분된 열
            r'(?:구분|항목|내용|조치|대상)\s*(?:\||:)',  # 테이블 헤더 패턴
        ]
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """PDF 파일에서 텍스트를 추출합니다."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                pages_text = []
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    # 페이지별 텍스트 정제
                    cleaned_text = self._clean_page_text(page_text)
                    if cleaned_text.strip():
                        pages_text.append(cleaned_text)
                
                # 전체 텍스트 결합
                full_text = "\n\n".join(pages_text)
                
                # 최종 정제
                return self._final_cleanup(full_text)
                
        except Exception as e:
            logger.error(f"PDF 텍스트 추출 실패: {pdf_path} - {str(e)}")
            raise
    
    def preprocess_pdf(self, pdf_path: str) -> dict:
        """PDF를 전처리하여 구조화된 텍스트 반환"""
        try:
            # 1. 텍스트 추출
            raw_text = self.extract_text_from_pdf(pdf_path)
            
            # 2. 구조 분석
            sections = self._identify_sections(raw_text)
            
            # 3. 테이블 감지 및 마크다운 변환
            markdown_text = self._convert_to_markdown(raw_text, sections)
            
            # 4. 메타데이터 추출
            metadata = self._extract_metadata(raw_text, os.path.basename(pdf_path))
            
            return {
                'raw_text': raw_text,
                'markdown_text': markdown_text,
                'sections': sections,
                'metadata': metadata,
                'file_path': pdf_path
            }
            
        except Exception as e:
            logger.error(f"PDF 전처리 실패: {pdf_path} - {str(e)}")
            raise
    
    def _clean_page_text(self, text: str) -> str:
        """페이지 텍스트 정제"""
        # 머리글/바닥글 제거
        for pattern in self.header_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # 연속된 공백 정리
        text = re.sub(r'\s+', ' ', text)
        
        # 줄바꿈 정리
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _final_cleanup(self, text: str) -> str:
        """최종 텍스트 정제"""
        # 특수문자 정리
        text = re.sub(r'[^\w\s\d가-힣.,;:!?()[\]{}""''`~@#$%^&*+=/<>|\\-]', ' ', text)
        
        # 중복 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        # 문장 사이 공백 정리
        text = re.sub(r'\.\s+', '. ', text)
        text = re.sub(r',\s+', ', ', text)
        
        return text.strip()
    
    def _identify_sections(self, text: str) -> List[dict]:
        """문서의 주요 섹션 식별"""
        sections = []
        
        # 주요 섹션 패턴
        section_patterns = [
            (r'의\s*안\s*개\s*요', 'overview'),
            (r'의\s*결\s*주\s*문', 'decision'),
            (r'제\s*재\s*내\s*용', 'sanctions'),
            (r'조\s*치\s*내\s*용', 'actions'),
            (r'위\s*반\s*사\s*실', 'violations'),
            (r'검\s*토\s*의\s*견', 'review'),
            (r'관\s*련\s*법\s*령', 'laws'),
        ]
        
        for pattern, section_type in section_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                sections.append({
                    'type': section_type,
                    'start': match.start(),
                    'end': match.end(),
                    'title': match.group()
                })
        
        # 위치순 정렬
        sections.sort(key=lambda x: x['start'])
        
        return sections
    
    def _convert_to_markdown(self, text: str, sections: List[dict]) -> str:
        """텍스트를 마크다운 형식으로 변환"""
        markdown_parts = []
        
        # 섹션별 처리
        for i, section in enumerate(sections):
            start = section['start']
            end = sections[i + 1]['start'] if i + 1 < len(sections) else len(text)
            
            section_text = text[start:end]
            
            # 섹션 제목
            markdown_parts.append(f"\n## {section['title']}\n")
            
            # 테이블 감지 및 변환
            if self._contains_table(section_text):
                table_markdown = self._convert_table_to_markdown(section_text)
                markdown_parts.append(table_markdown)
            else:
                # 일반 텍스트 처리
                processed_text = self._process_regular_text(section_text)
                markdown_parts.append(processed_text)
        
        return '\n'.join(markdown_parts)
    
    def _contains_table(self, text: str) -> bool:
        """텍스트에 테이블이 포함되어 있는지 확인"""
        for pattern in self.table_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _convert_table_to_markdown(self, text: str) -> str:
        """테이블을 마크다운 형식으로 변환"""
        lines = text.split('\n')
        markdown_lines = []
        
        in_table = False
        table_rows = []
        
        for line in lines:
            # 테이블 행 감지
            if '│' in line or '|' in line or re.search(r'\s{2,}', line):
                if not in_table:
                    in_table = True
                    markdown_lines.append('\n')
                
                # 테이블 행 파싱
                cells = re.split(r'[│|]|\s{2,}', line)
                cells = [cell.strip() for cell in cells if cell.strip()]
                
                if cells:
                    table_rows.append(cells)
            else:
                # 테이블 종료
                if in_table and table_rows:
                    # 마크다운 테이블 생성
                    markdown_table = self._create_markdown_table(table_rows)
                    markdown_lines.append(markdown_table)
                    table_rows = []
                    in_table = False
                
                # 일반 텍스트
                if line.strip():
                    markdown_lines.append(line.strip())
        
        # 마지막 테이블 처리
        if table_rows:
            markdown_table = self._create_markdown_table(table_rows)
            markdown_lines.append(markdown_table)
        
        return '\n'.join(markdown_lines)
    
    def _create_markdown_table(self, rows: List[List[str]]) -> str:
        """행 데이터로부터 마크다운 테이블 생성"""
        if not rows:
            return ""
        
        # 열 개수 정규화
        max_cols = max(len(row) for row in rows)
        normalized_rows = []
        for row in rows:
            normalized_row = row + [''] * (max_cols - len(row))
            normalized_rows.append(normalized_row)
        
        # 마크다운 테이블 생성
        table_lines = []
        
        # 헤더
        header = normalized_rows[0]
        table_lines.append('| ' + ' | '.join(header) + ' |')
        table_lines.append('|' + '|'.join(['---' for _ in header]) + '|')
        
        # 데이터 행
        for row in normalized_rows[1:]:
            table_lines.append('| ' + ' | '.join(row) + ' |')
        
        return '\n'.join(table_lines) + '\n'
    
    def _process_regular_text(self, text: str) -> str:
        """일반 텍스트 처리"""
        # 문단 구분
        paragraphs = text.split('\n\n')
        processed_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            if para:
                # 리스트 항목 감지
                if re.match(r'^[가-하\d]+\.\s', para):
                    para = '- ' + para
                processed_paragraphs.append(para)
        
        return '\n\n'.join(processed_paragraphs)
    
    def _extract_metadata(self, text: str, filename: str) -> dict:
        """문서 메타데이터 추출"""
        metadata = {
            'filename': filename,
            'year': None,
            'decision_id': None,
            'agenda_no': None,
        }
        
        # 파일명에서 연도와 호수 추출
        filename_match = re.search(r'(\d{4}).*?(\d+)호', filename)
        if filename_match:
            metadata['year'] = int(filename_match.group(1))
            metadata['decision_id'] = int(filename_match.group(2))
        
        # 의안번호 추출
        agenda_match = re.search(r'의안번호\s*[:：]?\s*제?\s*(\d+)\s*호', text)
        if agenda_match:
            metadata['agenda_no'] = f"제 {agenda_match.group(1)} 호"
        
        return metadata