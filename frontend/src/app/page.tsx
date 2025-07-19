'use client';

import React, { useState } from 'react';
import MainLayout from "@/components/layout/MainLayout";
import SearchInterface from "@/components/search/SearchInterface";
import SearchResults from "@/components/results/SearchResults";
import Dashboard from "@/components/dashboard/Dashboard";

export default function Home() {
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = async (query: string, filters?: any) => {
    setSearchQuery(query);
    setLoading(true);
    
    try {
      const { searchService } = await import('@/lib/api');
      
      let response;
      if (filters && Object.values(filters).some(v => v !== undefined)) {
        // 고급 검색
        response = await searchService.advancedSearch({
          keyword: query,
          ...filters,
          limit: 50
        });
      } else {
        // 자연어 검색
        response = await searchService.naturalLanguageSearch({
          query: query,
          limit: 50
        });
      }
      
      setSearchResults(response.results || []);
      setLoading(false);
      
    } catch (error) {
      console.error('Search error:', error);
      setLoading(false);
      
      // API 실패 시 임시 데이터 표시 (개발 중)
      const mockResults = [
        {
          decision_id: 195,
          decision_year: 2025,
          title: '엔에이치아문디자산운용에 대한 정기검사 결과 조치안',
          category_1: '제재',
          category_2: '기관',
          stated_purpose: '엔에이치아문디자산운용㈜에 대한 정기검사 결과 법규 위반사항에 대해 조치',
          entity_name: '엔에이치아문디자산운용㈜',
          industry_sector: '금융투자',
          action_type: '과징금',
          fine_amount: 7413000000, // 741.3백만원 = 74.13억원
          violation_details: '신주인수권부사채 회계처리 기준 위반',
        },
        {
          decision_id: 194,
          decision_year: 2025,
          title: '한국대성자산운용㈜에 대한 수시검사 결과 조치안',
          category_1: '제재',
          category_2: '기관',
          stated_purpose: '한국대성자산운용㈜에 대한 수시검사 결과 법규 위반사항에 대해 조치',
          entity_name: '한국대성자산운용㈜',
          industry_sector: '금융투자',
          action_type: '과태료',
          fine_amount: 50000000, // 5천만원
          violation_details: '내부통제 기준 위반',
        }
      ];
      
      setTimeout(() => {
        setSearchResults(mockResults);
        setLoading(false);
      }, 500);
    }
  };

  return (
    <MainLayout>
      <div className="min-h-screen space-y-8">
        <SearchInterface onSearch={handleSearch} />
        
        {(searchResults.length > 0 || loading) && (
          <SearchResults
            results={searchResults}
            loading={loading}
            searchQuery={searchQuery}
            totalCount={searchResults.length}
          />
        )}
        
        {searchResults.length === 0 && !loading && (
          <Dashboard />
        )}
      </div>
    </MainLayout>
  );
}
