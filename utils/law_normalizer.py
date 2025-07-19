#!/usr/bin/env python3
"""
법률명 정규화 모듈
FSC 법률 데이터베이스를 활용한 법률명 표준화
"""
import json
import re
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class LawNormalizer:
    """법률명 정규화 클래스"""
    
    def __init__(self, laws_json_path: str = './fsc_laws_with_abbreviations.json'):
        """초기화"""
        self.laws_data = self._load_laws_data(laws_json_path)
        self.name_to_abbr = {}
        self.abbr_to_name = {}
        self._build_lookup_tables()
        
    def _load_laws_data(self, json_path: str) -> Dict:
        """법률 데이터 로드"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"법률 데이터 로드 실패: {e}")
            return {'laws': []}
    
    def _build_lookup_tables(self):
        """검색용 테이블 구축"""
        for law in self.laws_data.get('laws', []):
            law_name = law['law_name']
            # API에서 제공하는 공식 약칭과 크롤링 약칭 모두 활용
            short_name_api = law.get('law_short_name_api', '')
            short_name = law.get('law_short_name', '')
            
            # 우선순위: API 약칭 > 크롤링 약칭
            preferred_short_name = short_name_api or short_name
            
            # 정식 명칭 -> 약칭 매핑 (약칭이 있는 경우만)
            if preferred_short_name:
                self.name_to_abbr[law_name] = preferred_short_name
                
                # 약칭 -> 정식 명칭 매핑
                self.abbr_to_name[preferred_short_name] = law_name
                
                # 변형된 형태도 추가 (공백 제거, 띄어쓰기 정규화 등)
                normalized_name = self._normalize_spaces(law_name)
                if normalized_name != law_name:
                    self.name_to_abbr[normalized_name] = preferred_short_name
                
                # 공백 제거 버전도 추가
                no_space_name = law_name.replace(' ', '')
                if no_space_name != law_name:
                    self.name_to_abbr[no_space_name] = preferred_short_name
                
    def _normalize_spaces(self, text: str) -> str:
        """공백 정규화"""
        # 연속된 공백을 하나로
        text = re.sub(r'\s+', ' ', text)
        # 앞뒤 공백 제거
        text = text.strip()
        return text
    
    def normalize_law_name(self, law_name: str) -> str:
        """
        법률명을 표준 약칭으로 정규화
        
        Args:
            law_name: 원본 법률명
            
        Returns:
            표준화된 법률명 (약칭)
        """
        if not law_name:
            return law_name
            
        # 공백 정규화
        law_name = self._normalize_spaces(law_name)
        
        # 이미 약칭인 경우
        if law_name in self.abbr_to_name:
            return law_name
            
        # 정식 명칭인 경우 약칭으로 변환
        if law_name in self.name_to_abbr:
            abbr = self.name_to_abbr[law_name]
            if abbr:  # 약칭이 있는 경우만 변환
                return abbr
                
        # 부분 매칭 시도
        for full_name, abbr in self.name_to_abbr.items():
            if full_name in law_name or law_name in full_name:
                if abbr:  # 약칭이 있는 경우만 변환
                    logger.debug(f"부분 매칭: {law_name} -> {abbr}")
                    return abbr
                    
        # 특수 케이스 처리 (API에서 약칭이 없는 경우 대비)
        if '자본시장과금융투자업에관한법률' in law_name.replace(' ', ''):
            return '자본시장법'
        elif '금융회사의지배구조에관한법률' in law_name.replace(' ', ''):
            return '금융사지배구조법'
        elif '신용정보의이용및보호에관한법률' in law_name.replace(' ', ''):
            return '신용정보법'
            
        # 변환할 수 없는 경우 원본 반환
        logger.debug(f"법률명 정규화 실패: {law_name}")
        return law_name
    
    def find_best_match(self, law_name: str) -> Optional[str]:
        """
        가장 적합한 법률 매칭 찾기
        
        Args:
            law_name: 검색할 법률명
            
        Returns:
            매칭된 표준 약칭
        """
        if not law_name:
            return None
            
        # 공백 정규화
        law_name = self._normalize_spaces(law_name)
        
        # 1. 정확한 매칭
        if law_name in self.name_to_abbr:
            return self.name_to_abbr[law_name]
        
        # 2. 공백 제거 후 매칭
        no_space_name = law_name.replace(' ', '')
        if no_space_name in self.name_to_abbr:
            return self.name_to_abbr[no_space_name]
        
        # 3. 포함 관계 매칭 (더 정확한 버전)
        best_match = None
        max_match_length = 0
        
        for full_name, abbr in self.name_to_abbr.items():
            full_name_clean = full_name.replace(' ', '').lower()
            law_name_clean = law_name.replace(' ', '').lower()
            
            # 양방향 포함 검사
            if (full_name_clean in law_name_clean or law_name_clean in full_name_clean):
                # 더 긴 매칭을 우선으로
                match_length = min(len(full_name_clean), len(law_name_clean))
                if match_length > max_match_length:
                    max_match_length = match_length
                    best_match = abbr
        
        if best_match:
            logger.debug(f"부분 매칭 성공: {law_name} -> {best_match}")
            return best_match
        
        return None
    
    def get_law_info(self, law_name: str) -> Optional[Dict]:
        """
        법률명으로 상세 정보 조회
        
        Args:
            law_name: 법률명
            
        Returns:
            법률 상세 정보 딕셔너리
        """
        normalized = self.normalize_law_name(law_name)
        
        # 약칭으로 정식명칭 찾기
        full_name = self.get_full_name(normalized)
        if not full_name:
            return None
        
        # 상세 정보 찾기
        for law in self.laws_data.get('laws', []):
            if law['law_name'] == full_name:
                return law
        
        return None
    
    def normalize_law_list(self, laws: List[str]) -> List[str]:
        """
        법률명 리스트를 정규화하고 중복 제거
        
        Args:
            laws: 법률명 리스트
            
        Returns:
            정규화되고 중복이 제거된 법률명 리스트
        """
        normalized = []
        seen = set()
        
        for law in laws:
            normalized_law = self.normalize_law_name(law)
            if normalized_law not in seen:
                seen.add(normalized_law)
                normalized.append(normalized_law)
                
        return normalized
    
    def get_full_name(self, law_name: str) -> Optional[str]:
        """약칭에서 정식 명칭 조회"""
        return self.abbr_to_name.get(law_name)
    
    def get_abbreviation(self, law_name: str) -> Optional[str]:
        """정식 명칭에서 약칭 조회"""
        return self.name_to_abbr.get(law_name)

# 싱글톤 인스턴스
_normalizer_instance = None

def get_law_normalizer() -> LawNormalizer:
    """법률명 정규화기 싱글톤 인스턴스 반환"""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = LawNormalizer()
    return _normalizer_instance

if __name__ == "__main__":
    # 테스트
    normalizer = get_law_normalizer()
    
    test_cases = [
        "자본시장과 금융투자업에 관한 법률",
        "자본시장과금융투자업에관한법률",
        "자본시장법",
        "금융회사의 지배구조에 관한 법률",
        "금융사지배구조법",
        "신용정보의 이용 및 보호에 관한 법률",
        "전자금융거래법",
        "보험업법"
    ]
    
    print("법률명 정규화 테스트:\n")
    for law_name in test_cases:
        normalized = normalizer.normalize_law_name(law_name)
        print(f"{law_name:40s} -> {normalized}")
    
    # 리스트 정규화 테스트
    print("\n리스트 정규화 테스트:")
    law_list = [
        "자본시장과 금융투자업에 관한 법률",
        "자본시장법",
        "금융회사의 지배구조에 관한 법률",
        "금융사지배구조법",
        "지배구조법"  # 중복
    ]
    normalized_list = normalizer.normalize_law_list(law_list)
    print(f"원본 리스트 ({len(law_list)}개): {law_list}")
    print(f"정규화 리스트 ({len(normalized_list)}개): {normalized_list}")