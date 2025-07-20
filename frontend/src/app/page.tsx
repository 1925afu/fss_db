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
    // 새로운 검색 시작 시 이전 결과 즉시 초기화
    setSearchResults([]);
    
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
      
      // V2 API 응답 구조 처리
      setSearchResults(response.results || []);
      setLoading(false);
      
    } catch (error: any) {
      console.error('Search error:', error);
      
      // API 실패 시 더 자세한 에러 메시지 표시
      const errorMessage = error.response?.data?.detail || error.message || '검색 중 오류가 발생했습니다.';
      console.error('API Error details:', errorMessage);
      
      // 에러 발생 시 빈 결과 반환
      setSearchResults([]);
      setLoading(false);
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
        
        {/* 대시보드는 항상 표시 */}
        <div className="dashboard-section">
          <h2 className="text-2xl font-bold mb-6">분석 대시보드</h2>
          <Dashboard />
        </div>
      </div>
    </MainLayout>
  );
}
