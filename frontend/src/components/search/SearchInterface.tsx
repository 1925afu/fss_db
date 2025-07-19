'use client';

import React, { useState } from 'react';
import { 
  Card, 
  Input, 
  Button, 
  Space, 
  Row, 
  Col, 
  Typography, 
  Tag,
  Divider,
  Select,
  DatePicker,
  InputNumber
} from 'antd';
import { 
  SearchOutlined, 
  FilterOutlined, 
  ClearOutlined,
  HistoryOutlined,
  BulbOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface SearchInterfaceProps {
  onSearch?: (query: string, filters?: any) => void;
}

export default function SearchInterface({ onSearch }: SearchInterfaceProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [filters, setFilters] = useState({
    category1: undefined,
    category2: undefined,
    industry: undefined,
    actionType: undefined,
    year: undefined,
    minAmount: undefined,
    maxAmount: undefined,
  });

  // 검색 예시 제안
  const searchSuggestions = [
    "엔에이치아문디자산운용 제재 내역",
    "10억원 이상 과징금 부과 사건",
    "독립성 위반으로 징계받은 공인회계사",
    "2024년 제재 의결 현황",
    "회계처리 기준 위반 제재 현황",
    "직무정지 처분을 받은 회계사"
  ];

  const handleSearch = () => {
    if (!searchQuery.trim()) return;
    
    const searchParams = {
      query: searchQuery,
      filters: showAdvanced ? filters : undefined
    };
    
    onSearch?.(searchQuery, showAdvanced ? filters : undefined);
  };

  const handleSuggestionClick = (suggestion: string) => {
    setSearchQuery(suggestion);
  };

  const clearFilters = () => {
    setFilters({
      category1: undefined,
      category2: undefined,
      industry: undefined,
      actionType: undefined,
      year: undefined,
      minAmount: undefined,
      maxAmount: undefined,
    });
  };

  return (
    <div className="mb-8">
      {/* 메인 검색 영역 */}
      <Card className="shadow-lg border-0">
        <Row gutter={[24, 24]}>
          <Col span={24}>
            <Title level={2} className="text-center mb-6">
              금융위원회 의결서 검색
            </Title>
            <Text className="block text-center text-gray-600 mb-8">
              자연어로 질문하시면 AI가 관련 의결서를 찾아드립니다
            </Text>
          </Col>
          
          <Col span={24}>
            <Space.Compact style={{ width: '100%' }} size="large">
              <TextArea
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="예: 신한은행이 2025년에 받은 제재 내역을 알려주세요"
                autoSize={{ minRows: 2, maxRows: 4 }}
                style={{ flex: 1 }}
                onPressEnter={(e) => {
                  if (!e.shiftKey) {
                    e.preventDefault();
                    handleSearch();
                  }
                }}
              />
              <Button 
                type="primary" 
                size="large"
                icon={<SearchOutlined />}
                onClick={handleSearch}
                disabled={!searchQuery.trim()}
                style={{ height: 'auto', minHeight: '60px' }}
              >
                검색
              </Button>
            </Space.Compact>
          </Col>

          {/* 고급 검색 토글 */}
          <Col span={24}>
            <div className="text-center">
              <Button 
                type="link" 
                icon={<FilterOutlined />}
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                {showAdvanced ? '기본 검색' : '고급 검색'}
              </Button>
            </div>
          </Col>

          {/* 고급 검색 필터 */}
          {showAdvanced && (
            <Col span={24}>
              <Card type="inner" title="상세 검색 조건">
                <Row gutter={[16, 16]}>
                  <Col xs={24} sm={12} md={6}>
                    <Text strong>대분류</Text>
                    <Select
                      placeholder="선택하세요"
                      value={filters.category1}
                      onChange={(value) => setFilters(prev => ({ ...prev, category1: value }))}
                      style={{ width: '100%', marginTop: 4 }}
                      allowClear
                    >
                      <Select.Option value="제재">제재</Select.Option>
                      <Select.Option value="인허가">인허가</Select.Option>
                      <Select.Option value="정책">정책</Select.Option>
                    </Select>
                  </Col>

                  <Col xs={24} sm={12} md={6}>
                    <Text strong>중분류</Text>
                    <Select
                      placeholder="선택하세요"
                      value={filters.category2}
                      onChange={(value) => setFilters(prev => ({ ...prev, category2: value }))}
                      style={{ width: '100%', marginTop: 4 }}
                      allowClear
                    >
                      <Select.Option value="기관">기관</Select.Option>
                      <Select.Option value="임직원">임직원</Select.Option>
                      <Select.Option value="전문가">전문가</Select.Option>
                    </Select>
                  </Col>

                  <Col xs={24} sm={12} md={6}>
                    <Text strong>업권</Text>
                    <Select
                      placeholder="선택하세요"
                      value={filters.industry}
                      onChange={(value) => setFilters(prev => ({ ...prev, industry: value }))}
                      style={{ width: '100%', marginTop: 4 }}
                      allowClear
                    >
                      <Select.Option value="은행">은행</Select.Option>
                      <Select.Option value="보험">보험</Select.Option>
                      <Select.Option value="금융투자">금융투자</Select.Option>
                      <Select.Option value="회계/감사">회계/감사</Select.Option>
                    </Select>
                  </Col>

                  <Col xs={24} sm={12} md={6}>
                    <Text strong>조치유형</Text>
                    <Select
                      placeholder="선택하세요"
                      value={filters.actionType}
                      onChange={(value) => setFilters(prev => ({ ...prev, actionType: value }))}
                      style={{ width: '100%', marginTop: 4 }}
                      allowClear
                    >
                      <Select.Option value="과징금">과징금</Select.Option>
                      <Select.Option value="과태료">과태료</Select.Option>
                      <Select.Option value="직무정지">직무정지</Select.Option>
                      <Select.Option value="기관경고">기관경고</Select.Option>
                    </Select>
                  </Col>

                  <Col xs={24} sm={8}>
                    <Text strong>의결연도</Text>
                    <Select
                      placeholder="연도 선택"
                      value={filters.year}
                      onChange={(value) => setFilters(prev => ({ ...prev, year: value }))}
                      style={{ width: '100%', marginTop: 4 }}
                      allowClear
                    >
                      <Select.Option value={2025}>2025년</Select.Option>
                      <Select.Option value={2024}>2024년</Select.Option>
                      <Select.Option value={2023}>2023년</Select.Option>
                    </Select>
                  </Col>

                  <Col xs={24} sm={8}>
                    <Text strong>최소 과징금 (만원)</Text>
                    <InputNumber
                      placeholder="0"
                      value={filters.minAmount}
                      onChange={(value) => setFilters(prev => ({ ...prev, minAmount: value }))}
                      style={{ width: '100%', marginTop: 4 }}
                      min={0}
                      formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    />
                  </Col>

                  <Col xs={24} sm={8}>
                    <Text strong>최대 과징금 (만원)</Text>
                    <InputNumber
                      placeholder="제한없음"
                      value={filters.maxAmount}
                      onChange={(value) => setFilters(prev => ({ ...prev, maxAmount: value }))}
                      style={{ width: '100%', marginTop: 4 }}
                      min={0}
                      formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    />
                  </Col>

                  <Col span={24}>
                    <div className="text-center">
                      <Button 
                        icon={<ClearOutlined />}
                        onClick={clearFilters}
                      >
                        필터 초기화
                      </Button>
                    </div>
                  </Col>
                </Row>
              </Card>
            </Col>
          )}
        </Row>
      </Card>

      {/* 검색 제안 */}
      <Card className="mt-6" title={
        <Space>
          <BulbOutlined style={{ color: '#faad14' }} />
          <span>검색 예시</span>
        </Space>
      }>
        <Row gutter={[8, 8]}>
          {searchSuggestions.map((suggestion, index) => (
            <Col key={index}>
              <Tag 
                className="cursor-pointer hover:bg-blue-50"
                onClick={() => handleSuggestionClick(suggestion)}
              >
                {suggestion}
              </Tag>
            </Col>
          ))}
        </Row>
        
        <Divider />
        
        <div className="text-gray-500 text-sm">
          <Row gutter={[24, 8]}>
            <Col xs={24} md={12}>
              <strong>💡 검색 팁:</strong>
              <ul className="ml-4 mt-2">
                <li>회사명, 기관명으로 검색 가능</li>
                <li>위반 내용, 조치 유형으로 검색 가능</li>
                <li>금액 조건으로 검색 가능</li>
              </ul>
            </Col>
            <Col xs={24} md={12}>
              <strong>🔍 검색 예시:</strong>
              <ul className="ml-4 mt-2">
                <li>"신한은행 과징금"</li>
                <li>"독립성 위반 회계사"</li>
                <li>"5억원 이상 제재"</li>
              </ul>
            </Col>
          </Row>
        </div>
      </Card>
    </div>
  );
}