#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import PyPDF2
import re
import os
from pathlib import Path
import json

class LawReferenceAnalyzer:
    def __init__(self):
        self.law_patterns = {
            'law_name': re.compile(r'｢([^｣]+)｣'),
            'article': re.compile(r'제(\d+)조'),
            'paragraph': re.compile(r'제(\d+)항'),
            'item': re.compile(r'제(\d+)호'),
            'full_reference': re.compile(r'제(\d+)조(?:\s*제(\d+)항)?(?:\s*제(\d+)호)?'),
            'enforcement_decree': re.compile(r'시행령'),
            'enforcement_rule': re.compile(r'시행규칙'),
            'section_headers': re.compile(r'(근거법규|법적근거|근거조항|법령|관련법규)', re.IGNORECASE)
        }
        
    def extract_text_from_pdf(self, pdf_path):
        """PDF에서 텍스트 추출"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    
    def find_law_sections(self, text):
        """근거법규 섹션 찾기"""
        sections = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            if self.law_patterns['section_headers'].search(line):
                # 섹션 헤더를 찾으면 이후 내용 수집
                section_content = []
                section_start = i
                
                # 다음 섹션이나 문서 끝까지 수집
                for j in range(i+1, min(i+50, len(lines))):
                    if j < len(lines):
                        section_content.append(lines[j])
                        # 다른 주요 섹션이 시작되면 중단
                        if any(keyword in lines[j] for keyword in ['처분 내용', '조치 내용', '검사 결과']):
                            break
                
                sections.append({
                    'header': line.strip(),
                    'line_number': section_start,
                    'content': '\n'.join(section_content)
                })
        
        return sections
    
    def analyze_law_references(self, text):
        """법률 참조 분석"""
        analysis = {
            'law_names': [],
            'articles': [],
            'full_references': [],
            'enforcement_decrees': [],
            'enforcement_rules': []
        }
        
        # 법률명 추출 (｢｣ 기호로 묶인 것)
        law_names = self.law_patterns['law_name'].findall(text)
        analysis['law_names'] = list(set(law_names))
        
        # 전체 조항 참조 추출
        full_refs = self.law_patterns['full_reference'].findall(text)
        for ref in full_refs:
            article = ref[0]
            paragraph = ref[1] if ref[1] else None
            item = ref[2] if ref[2] else None
            
            ref_str = f"제{article}조"
            if paragraph:
                ref_str += f" 제{paragraph}항"
            if item:
                ref_str += f" 제{item}호"
            
            analysis['full_references'].append(ref_str)
        
        # 시행령/시행규칙 확인
        if self.law_patterns['enforcement_decree'].search(text):
            analysis['enforcement_decrees'] = True
        if self.law_patterns['enforcement_rule'].search(text):
            analysis['enforcement_rules'] = True
            
        return analysis
    
    def analyze_file(self, pdf_path):
        """단일 파일 분석"""
        filename = os.path.basename(pdf_path)
        print(f"\n분석 중: {filename}")
        
        text = self.extract_text_from_pdf(pdf_path)
        if text.startswith("Error"):
            return {'filename': filename, 'error': text}
        
        # 근거법규 섹션 찾기
        law_sections = self.find_law_sections(text)
        
        # 전체 텍스트에서 법률 참조 분석
        full_analysis = self.analyze_law_references(text)
        
        # 근거법규 섹션별 상세 분석
        section_analyses = []
        for section in law_sections:
            section_analysis = self.analyze_law_references(section['content'])
            section_analysis['header'] = section['header']
            section_analysis['line_number'] = section['line_number']
            section_analyses.append(section_analysis)
        
        # 업권 파악
        industry = "기타"
        if "저축은행" in filename:
            industry = "저축은행"
        elif "생명보험" in filename:
            industry = "생명보험"
        elif "은행" in filename and "저축은행" not in filename:
            industry = "은행"
        elif "증권" in filename:
            industry = "증권"
        elif "자산운용" in filename:
            industry = "자산운용"
        
        return {
            'filename': filename,
            'industry': industry,
            'law_sections_found': len(law_sections),
            'law_sections': section_analyses,
            'overall_analysis': full_analysis,
            'sample_text': text[:500] if len(text) > 500 else text  # 샘플 텍스트
        }

def main():
    # PDF 파일 목록
    pdf_files = [
        "금융위 의결서(제2024-394호)_(서울)에스비아이저축은행에 대한 정기검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2024-395호)_(경북)라온저축은행에 대한 수시검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2024-397호)_삼성생명보험㈜에 대한 수시검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2024-398호)_미래에셋생명보험㈜에 대한 수시검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2024-399호)_동양생명보험㈜에 대한 수시검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2024-400호)_흥국생명보험㈜에 대한 수시검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2024-401호)_에이비엘생명보험㈜에 대한 수시검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2024-402호)_푸본현대생명보험㈜에 대한 수시검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2024-403호)_한화생명보험㈜에 대한 수시검사 결과 조치안(공개용).pdf",
        "금융위 의결서(제2024-404호)_신한라이프생명보험㈜에 대한 수시검사 결과 조치안(공개용).pdf"
    ]
    
    base_path = Path("/mnt/c/Users/1925a/Documents/fss_db/data/processed_pdf")
    analyzer = LawReferenceAnalyzer()
    
    results = []
    industry_patterns = {}
    
    for pdf_file in pdf_files:
        pdf_path = base_path / pdf_file
        if pdf_path.exists():
            result = analyzer.analyze_file(str(pdf_path))
            results.append(result)
            
            # 업권별 패턴 수집
            industry = result['industry']
            if industry not in industry_patterns:
                industry_patterns[industry] = {
                    'files': [],
                    'common_laws': [],
                    'reference_patterns': []
                }
            
            industry_patterns[industry]['files'].append(result['filename'])
            if 'overall_analysis' in result:
                industry_patterns[industry]['common_laws'].extend(result['overall_analysis']['law_names'])
                industry_patterns[industry]['reference_patterns'].extend(result['overall_analysis']['full_references'])
    
    # 결과 출력
    print("\n" + "="*80)
    print("분석 결과 요약")
    print("="*80)
    
    for result in results:
        print(f"\n[{result['filename']}]")
        print(f"업권: {result['industry']}")
        print(f"근거법규 섹션 수: {result['law_sections_found']}")
        
        if result['law_sections']:
            print("\n근거법규 섹션:")
            for section in result['law_sections']:
                print(f"  - {section['header']} (라인 {section['line_number']})")
                if section['law_names']:
                    print(f"    법률명: {', '.join(section['law_names'][:3])}")
                if section['full_references']:
                    print(f"    조항 예시: {', '.join(section['full_references'][:3])}")
        
        if 'overall_analysis' in result and result['overall_analysis']['law_names']:
            print(f"\n주요 참조 법률:")
            for law in result['overall_analysis']['law_names'][:5]:
                print(f"  - ｢{law}｣")
    
    # 업권별 패턴 요약
    print("\n" + "="*80)
    print("업권별 법률 표기 패턴")
    print("="*80)
    
    for industry, patterns in industry_patterns.items():
        print(f"\n[{industry}]")
        print(f"분석 파일 수: {len(patterns['files'])}")
        
        # 가장 많이 참조된 법률
        common_laws = {}
        for law in patterns['common_laws']:
            common_laws[law] = common_laws.get(law, 0) + 1
        
        if common_laws:
            sorted_laws = sorted(common_laws.items(), key=lambda x: x[1], reverse=True)
            print(f"주요 참조 법률:")
            for law, count in sorted_laws[:3]:
                print(f"  - ｢{law}｣ ({count}회)")
        
        # 조항 표기 패턴
        ref_patterns = {}
        for ref in patterns['reference_patterns']:
            pattern = "제X조" if "항" not in ref and "호" not in ref else \
                     "제X조 제X항" if "항" in ref and "호" not in ref else \
                     "제X조 제X호" if "호" in ref and "항" not in ref else \
                     "제X조 제X항 제X호"
            ref_patterns[pattern] = ref_patterns.get(pattern, 0) + 1
        
        if ref_patterns:
            print(f"조항 표기 패턴:")
            for pattern, count in sorted(ref_patterns.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {pattern} ({count}회)")
    
    # 결과를 JSON 파일로 저장
    with open('/mnt/c/Users/1925a/Documents/fss_db/law_reference_analysis.json', 'w', encoding='utf-8') as f:
        json.dump({
            'individual_results': results,
            'industry_patterns': industry_patterns
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n상세 분석 결과가 law_reference_analysis.json 파일에 저장되었습니다.")

if __name__ == "__main__":
    main()