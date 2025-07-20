'use client';

import React, { useState } from 'react';
import { 
  Card, 
  Table, 
  Tag, 
  Space, 
  Typography, 
  Button, 
  Modal,
  Descriptions,
  Empty,
  Pagination,
  Row,
  Col,
  Statistic,
  Alert
} from 'antd';
import { 
  EyeOutlined, 
  DownloadOutlined, 
  InfoCircleOutlined,
  CalendarOutlined,
  DollarOutlined,
  TeamOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text, Paragraph } = Typography;

interface SearchResult {
  decision_id: number;
  decision_year: number;
  title: string;
  category_1: string;
  category_2: string;
  stated_purpose: string;
  entity_name?: string;
  industry_sector?: string;
  action_type?: string;
  fine_amount?: number;
  violation_details?: string;
  effective_date?: string;
}

interface SearchResultsProps {
  results: SearchResult[];
  loading?: boolean;
  searchQuery?: string;
  totalCount?: number;
  currentPage?: number;
  pageSize?: number;
  onPageChange?: (page: number, size: number) => void;
}

export default function SearchResults({ 
  results = [], 
  loading = false, 
  searchQuery = '',
  totalCount = 0,
  currentPage = 1,
  pageSize = 10,
  onPageChange
}: SearchResultsProps) {
  const [selectedRecord, setSelectedRecord] = useState<SearchResult | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);

  const formatAmount = (amount: number | null | undefined) => {
    if (!amount) return '-';
    return `${(amount / 10000).toLocaleString()}만원`;
  };

  const getActionColor = (actionType: string | undefined) => {
    if (!actionType) return 'default';
    if (actionType.includes('과징금')) return 'red';
    if (actionType.includes('과태료')) return 'orange';
    if (actionType.includes('직무정지')) return 'volcano';
    if (actionType.includes('기관경고')) return 'gold';
    return 'blue';
  };

  const getCategoryColor = (category: string | undefined) => {
    if (!category) return 'default';
    if (category === '제재') return 'red';
    if (category === '인허가') return 'green';
    if (category === '정책') return 'blue';
    return 'default';
  };

  const columns: ColumnsType<SearchResult> = [
    {
      title: '의결서 정보',
      key: 'decision_info',
      width: 200,
      render: (_, record) => (
        <div>
          <Text strong>
            {record.decision_year}-{record.decision_id}호
          </Text>
          <br />
          <Space size={4} wrap>
            <Tag color={getCategoryColor(record.category_1)} size="small">
              {record.category_1}
            </Tag>
            <Tag color="default" size="small">
              {record.category_2}
            </Tag>
          </Space>
        </div>
      ),
    },
    {
      title: '의안명',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (text) => (
        <Paragraph ellipsis={{ rows: 2, tooltip: text }} className="mb-0">
          {text}
        </Paragraph>
      ),
    },
    {
      title: '대상 기관/개인',
      key: 'target_info',
      width: 180,
      render: (_, record) => (
        <div>
          {record.entity_name && (
            <Text strong className="block">
              {record.entity_name}
            </Text>
          )}
          {record.industry_sector && (
            <Tag color="blue" size="small">
              {record.industry_sector}
            </Tag>
          )}
        </div>
      ),
    },
    {
      title: '조치 내용',
      key: 'action_info',
      width: 150,
      render: (_, record) => (
        <div>
          {record.action_type && (
            <Tag color={getActionColor(record.action_type)} className="mb-1">
              {record.action_type}
            </Tag>
          )}
          {record.fine_amount && record.fine_amount > 0 && (
            <div>
              <Text strong className="text-red-600">
                {formatAmount(record.fine_amount)}
              </Text>
            </div>
          )}
        </div>
      ),
    },
    {
      title: '액션',
      key: 'actions',
      width: 100,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="primary"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedRecord(record);
              setDetailVisible(true);
            }}
          >
            상세
          </Button>
        </Space>
      ),
    },
  ];

  const CardView = () => (
    <Row gutter={[16, 16]}>
      {results.map((result, index) => (
        <Col xs={24} sm={12} lg={8} key={index}>
          <Card
            size="small"
            hoverable
            actions={[
              <Button 
                key="detail"
                type="link" 
                icon={<EyeOutlined />}
                onClick={() => {
                  setSelectedRecord(result);
                  setDetailVisible(true);
                }}
              >
                상세보기
              </Button>
            ]}
          >
            <Card.Meta
              title={
                <div>
                  <Text strong className="text-sm">
                    {result.decision_year}-{result.decision_id}호
                  </Text>
                  <div className="mt-1">
                    <Space size={4} wrap>
                      <Tag color={getCategoryColor(result.category_1)} size="small">
                        {result.category_1}
                      </Tag>
                      <Tag color="default" size="small">
                        {result.category_2}
                      </Tag>
                    </Space>
                  </div>
                </div>
              }
              description={
                <div className="space-y-2">
                  <Paragraph 
                    ellipsis={{ rows: 2 }} 
                    className="mb-2 text-xs"
                  >
                    {result.title}
                  </Paragraph>
                  
                  {result.entity_name && (
                    <div>
                      <Text strong className="text-sm">
                        {result.entity_name}
                      </Text>
                      {result.industry_sector && (
                        <Tag color="blue" size="small" className="ml-2">
                          {result.industry_sector}
                        </Tag>
                      )}
                    </div>
                  )}
                  
                  {result.action_type && (
                    <div>
                      <Tag color={getActionColor(result.action_type)} size="small">
                        {result.action_type}
                      </Tag>
                      {result.fine_amount && result.fine_amount > 0 && (
                        <Text strong className="text-red-600 text-sm ml-2">
                          {formatAmount(result.fine_amount)}
                        </Text>
                      )}
                    </div>
                  )}
                </div>
              }
            />
          </Card>
        </Col>
      ))}
    </Row>
  );

  if (results.length === 0 && !loading) {
    return (
      <Card>
        <Empty
          description={
            searchQuery 
              ? `"${searchQuery}"에 대한 검색 결과가 없습니다.`
              : "검색어를 입력해주세요."
          }
        />
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* 검색 결과 요약 */}
      {searchQuery && results.length > 0 && (
        <Alert
          message={
            <Space>
              <InfoCircleOutlined />
              <span>
                "{searchQuery}"에 대한 검색 결과 {totalCount || results.length}건을 찾았습니다.
              </span>
            </Space>
          }
          type="info"
          showIcon={false}
          className="mb-4"
        />
      )}

      {/* 검색 결과 통계 */}
      {results.length > 0 && (
        <Row gutter={16} className="mb-4">
          <Col span={6}>
            <Statistic
              title="총 검색 결과"
              value={totalCount || results.length}
              suffix="건"
              valueStyle={{ fontSize: 16 }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="제재 건수"
              value={results.filter(r => r.category_1 === '제재').length}
              suffix="건"
              valueStyle={{ fontSize: 16, color: '#ff4d4f' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="과징금 건수"
              value={results.filter(r => r.action_type?.includes('과징금')).length}
              suffix="건"
              valueStyle={{ fontSize: 16, color: '#faad14' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="총 과징금"
              value={results.reduce((sum, r) => sum + (r.fine_amount || 0), 0) / 10000}
              suffix="만원"
              precision={0}
              valueStyle={{ fontSize: 16, color: '#52c41a' }}
            />
          </Col>
        </Row>
      )}

      {/* 데스크톱 테이블 뷰 */}
      <div className="hidden md:block">
        <Table
          columns={columns}
          dataSource={results}
          loading={loading}
          pagination={false}
          rowKey={(record) => `${record.decision_year}-${record.decision_id}`}
          size="small"
        />
      </div>

      {/* 모바일 카드 뷰 */}
      <div className="block md:hidden">
        <CardView />
      </div>

      {/* 페이지네이션 */}
      {totalCount && totalCount > pageSize && (
        <div className="text-center mt-4">
          <Pagination
            current={currentPage}
            total={totalCount}
            pageSize={pageSize}
            showSizeChanger
            showQuickJumper
            showTotal={(total, range) => 
              `${range[0]}-${range[1]} / 총 ${total}건`
            }
            onChange={onPageChange || (() => {})}
          />
        </div>
      )}

      {/* 상세 정보 모달 */}
      <Modal
        title={
          <Space>
            <InfoCircleOutlined />
            <span>의결서 상세 정보</span>
          </Space>
        }
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            닫기
          </Button>
        ]}
        width={800}
      >
        {selectedRecord && (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="의결서 번호" span={1}>
              {selectedRecord.decision_year}-{selectedRecord.decision_id}호
            </Descriptions.Item>
            <Descriptions.Item label="분류" span={1}>
              <Space>
                <Tag color={getCategoryColor(selectedRecord.category_1)}>
                  {selectedRecord.category_1}
                </Tag>
                <Tag>{selectedRecord.category_2}</Tag>
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="의안명" span={2}>
              {selectedRecord.title}
            </Descriptions.Item>
            <Descriptions.Item label="제안이유/목적" span={2}>
              <Text className="whitespace-pre-wrap">
                {selectedRecord.stated_purpose}
              </Text>
            </Descriptions.Item>
            {selectedRecord.entity_name && (
              <Descriptions.Item label="대상 기관/개인" span={1}>
                {selectedRecord.entity_name}
              </Descriptions.Item>
            )}
            {selectedRecord.industry_sector && (
              <Descriptions.Item label="업권" span={1}>
                <Tag color="blue">{selectedRecord.industry_sector}</Tag>
              </Descriptions.Item>
            )}
            {selectedRecord.action_type && (
              <Descriptions.Item label="조치 유형" span={1}>
                <Tag color={getActionColor(selectedRecord.action_type)}>
                  {selectedRecord.action_type}
                </Tag>
              </Descriptions.Item>
            )}
            {selectedRecord.fine_amount && selectedRecord.fine_amount > 0 && (
              <Descriptions.Item label="과징금/과태료" span={1}>
                <Text strong className="text-red-600">
                  {formatAmount(selectedRecord.fine_amount)}
                </Text>
              </Descriptions.Item>
            )}
            {selectedRecord.violation_details && (
              <Descriptions.Item label="위반 내용" span={2}>
                <Text className="whitespace-pre-wrap">
                  {selectedRecord.violation_details}
                </Text>
              </Descriptions.Item>
            )}
            {selectedRecord.violation_summary && (
              <Descriptions.Item label="AI 요약" span={2}>
                <Card size="small" className="bg-blue-50">
                  <Text className="whitespace-pre-wrap">
                    {selectedRecord.violation_summary}
                  </Text>
                </Card>
              </Descriptions.Item>
            )}
            {selectedRecord.effective_date && (
              <Descriptions.Item label="시행일" span={1}>
                <Space>
                  <CalendarOutlined />
                  {selectedRecord.effective_date}
                </Space>
              </Descriptions.Item>
            )}
            <Descriptions.Item label="관련 문서" span={2}>
              <Space direction="vertical" size="middle" className="w-full">
                {/* 금융위 의결서 */}
                <div>
                  <Button 
                    size="small"
                    icon={<FileTextOutlined />}
                    onClick={() => {
                      const year = selectedRecord.decision_year;
                      const id = selectedRecord.decision_id;
                      window.open(`http://localhost:8000/api/v1/decisions/${year}/${id}/download`, '_blank');
                    }}
                    type="primary"
                  >
                    금융위 의결서 (제{selectedRecord.decision_year}-{selectedRecord.decision_id}호)
                  </Button>
                </div>
                
                {/* 의결 파일 */}
                <div>
                  <Button 
                    size="small"
                    icon={<FileTextOutlined />}
                    onClick={async () => {
                      const year = selectedRecord.decision_year;
                      const id = selectedRecord.decision_id;
                      // 먼저 파일 존재 여부 확인을 위해 시도
                      try {
                        const response = await fetch(`http://localhost:8000/api/v1/decisions/${year}/${id}/companion-download`, {
                          method: 'HEAD'
                        });
                        if (response.ok) {
                          window.open(`http://localhost:8000/api/v1/decisions/${year}/${id}/companion-download`, '_blank');
                        } else {
                          // 파일이 없는 경우 아무 동작도 하지 않음
                          console.log('의결 파일이 없습니다.');
                        }
                      } catch (error) {
                        console.error('파일 확인 중 오류:', error);
                      }
                    }}
                  >
                    의결{selectedRecord.decision_id}. {selectedRecord.entity_name ? selectedRecord.entity_name : '관련 문서'}
                  </Button>
                  <Text type="secondary" className="text-xs ml-2">
                    (파일이 있는 경우에만 다운로드 가능)
                  </Text>
                </div>
              </Space>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}