'use client';

import React, { useEffect, useState } from 'react';
import { 
  Card, 
  Row, 
  Col, 
  Statistic, 
  Typography, 
  List, 
  Tag,
  Space,
  Progress,
  Timeline,
  Spin,
  Alert
} from 'antd';
import { 
  FileTextOutlined, 
  ExclamationCircleOutlined, 
  BookOutlined,
  TrophyOutlined,
  ClockCircleOutlined,
  BarChartOutlined,
  LoadingOutlined
} from '@ant-design/icons';
import { searchService, decisionsService } from '@/lib/api';

const { Title, Text } = Typography;

interface DashboardProps {
  data?: {
    totalDecisions?: number;
    totalActions?: number;
    totalLaws?: number;
  };
}

export default function Dashboard({ data }: DashboardProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [recentDecisions, setRecentDecisions] = useState<any[]>([]);

  // API에서 데이터 가져오기
  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      // 통계 데이터 가져오기
      const stats = await searchService.getSearchStats();
      
      // 최근 의결서 가져오기
      const decisions = await decisionsService.getDecisions({ limit: 5 });
      
      // 데이터 포맷팅
      const formattedData = {
        totalDecisions: stats.totals.decisions,
        totalActions: stats.totals.actions,
        totalLaws: stats.totals.laws,
        yearlyDistribution: stats.yearly_distribution,
        industryDistribution: stats.industry_distribution,
      };

      setDashboardData(formattedData);
      setRecentDecisions(Array.isArray(decisions) ? decisions : decisions.results || []);
      setLoading(false);
    } catch (error) {
      console.error('Dashboard data fetch error:', error);
      setError('데이터를 불러오는 중 오류가 발생했습니다.');
      setLoading(false);
      
      // 오류 시 임시 데이터 사용
      setDashboardData({
        totalDecisions: data?.totalDecisions || 58,
        totalActions: data?.totalActions || 59,
        totalLaws: data?.totalLaws || 30,
        yearlyDistribution: [],
        industryDistribution: []
      });
    }
  };

  // 임시 데이터 (API 실패 시 사용)
  const mockData = {
    recentDecisions: [
      {
        id: '2025-200',
        title: '공인회계사 ☆☆☆에 대한 징계의결안',
        date: '2025-01-15',
        type: '제재',
        category: '전문가'
      },
      {
        id: '2025-195',
        title: '엔에이치아문디자산운용에 대한 정기검사 결과 조치안',
        date: '2025-01-12',
        type: '제재',
        category: '기관'
      },
      {
        id: '2025-194',
        title: '한국대성자산운용㈜에 대한 수시검사 결과 조치안',
        date: '2025-01-10',
        type: '제재',
        category: '기관'
      }
    ],
    topViolations: [
      { type: '회계처리기준 위반', count: 5, percentage: 33 },
      { type: '독립성 위반', count: 3, percentage: 20 },
      { type: '내부통제 위반', count: 2, percentage: 13 },
      { type: '준법감시 소홀', count: 2, percentage: 13 },
      { type: '기타', count: 3, percentage: 21 }
    ],
    industryStats: [
      { sector: '금융투자', count: 8, percentage: 53 },
      { sector: '회계/감사', count: 4, percentage: 27 },
      { sector: '은행', count: 2, percentage: 13 },
      { sector: '보험', count: 1, percentage: 7 }
    ]
  };

  const stats = dashboardData || {
    totalDecisions: data?.totalDecisions || 0,
    totalActions: data?.totalActions || 0,
    totalLaws: data?.totalLaws || 0
  };

  // 로딩 상태
  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <Spin 
          indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />}
          size="large"
        />
      </div>
    );
  }

  // 에러 상태
  if (error) {
    return (
      <Alert
        message="데이터 로드 실패"
        description={error}
        type="error"
        showIcon
        closable
        onClose={() => setError(null)}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* 주요 통계 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="총 의결서"
              value={stats.totalDecisions}
              prefix={<FileTextOutlined />}
              suffix="건"
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="총 조치"
              value={stats.totalActions}
              prefix={<ExclamationCircleOutlined />}
              suffix="건"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="관련 법률"
              value={stats.totalLaws}
              prefix={<BookOutlined />}
              suffix="개"
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* 최근 의결서 */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                <ClockCircleOutlined />
                <span>최근 의결서</span>
              </Space>
            }
            className="h-full"
          >
            <List
              dataSource={recentDecisions.length > 0 ? recentDecisions.map((d, index) => ({
                id: `${d.decision_year}-${d.decision_id}`,
                key: `decision-${d.decision_year}-${d.decision_id}-${index}`,
                title: d.title,
                date: d.decision_month === 0 || d.decision_day === 0 
                  ? '날짜 정보 없음' 
                  : d.decision_date || `${d.decision_year}-${String(d.decision_month).padStart(2, '0')}-${String(d.decision_day).padStart(2, '0')}`,
                type: d.category_1,
                category: d.category_2
              })) : mockData.recentDecisions}
              renderItem={(item) => (
                <List.Item>
                  <div className="w-full">
                    <div className="flex justify-between items-start mb-2">
                      <Text strong className="text-sm">
                        의결서 제{item.id}호
                      </Text>
                      <Text type="secondary" className="text-xs">
                        {item.date}
                      </Text>
                    </div>
                    <Text className="block mb-2 text-sm">
                      {item.title}
                    </Text>
                    <Space>
                      <Tag color={item.type === '제재' ? 'red' : 'blue'}>
                        {item.type}
                      </Tag>
                      <Tag color="default">
                        {item.category}
                      </Tag>
                    </Space>
                  </div>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* 위반 유형별 통계 */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                <BarChartOutlined />
                <span>주요 위반 유형</span>
              </Space>
            }
            className="h-full"
          >
            <div className="space-y-4">
              {dashboardData?.violationStats ? 
                dashboardData.violationStats.map((item: any, index: number) => (
                  <div key={index}>
                    <div className="flex justify-between mb-1">
                      <Text className="text-sm">{item.type}</Text>
                      <Text className="text-sm text-gray-500">
                        {item.count}건 ({item.percentage}%)
                      </Text>
                    </div>
                    <Progress 
                      percent={item.percentage} 
                      showInfo={false}
                      strokeColor={
                        index === 0 ? '#ff4d4f' :
                        index === 1 ? '#faad14' :
                        index === 2 ? '#1677ff' : '#52c41a'
                      }
                    />
                  </div>
                )) : mockData.topViolations.map((item, index) => (
                <div key={index}>
                  <div className="flex justify-between mb-1">
                    <Text className="text-sm">{item.type}</Text>
                    <Text className="text-sm text-gray-500">
                      {item.count}건 ({item.percentage}%)
                    </Text>
                  </div>
                  <Progress 
                    percent={item.percentage} 
                    showInfo={false}
                    strokeColor={
                      index === 0 ? '#ff4d4f' :
                      index === 1 ? '#faad14' :
                      index === 2 ? '#1677ff' : '#52c41a'
                    }
                  />
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* 업권별 분포 */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                <TrophyOutlined />
                <span>업권별 제재 현황</span>
              </Space>
            }
          >
            <div className="space-y-4">
              {dashboardData?.industryDistribution ? 
                dashboardData.industryDistribution.slice(0, 4).map((item: any, index: number) => (
                  <div key={index} className="flex justify-between items-center">
                    <Space>
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ 
                          backgroundColor: 
                            index === 0 ? '#1677ff' :
                            index === 1 ? '#faad14' :
                            index === 2 ? '#52c41a' : '#f5222d'
                        }}
                      />
                      <Text>{item.sector}</Text>
                    </Space>
                    <Space>
                      <Text strong>{item.count}건</Text>
                      <Text type="secondary">({Math.round((item.count / stats.totalActions) * 100)}%)</Text>
                    </Space>
                  </div>
                )) : mockData.industryStats.map((item, index) => (
                <div key={index} className="flex justify-between items-center">
                  <Space>
                    <div 
                      className="w-3 h-3 rounded-full"
                      style={{ 
                        backgroundColor: 
                          index === 0 ? '#1677ff' :
                          index === 1 ? '#faad14' :
                          index === 2 ? '#52c41a' : '#f5222d'
                      }}
                    />
                    <Text>{item.sector}</Text>
                  </Space>
                  <Space>
                    <Text strong>{item.count}건</Text>
                    <Text type="secondary">({item.percentage}%)</Text>
                  </Space>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        {/* 처리 진행 상황 */}
        <Col xs={24} lg={12}>
          <Card title="시스템 현황">
            <Timeline
              items={[
                {
                  color: 'green',
                  children: (
                    <div>
                      <Text strong>데이터 수집 완료</Text>
                      <br />
                      <Text type="secondary">2025년 의결서 {stats.totalDecisions}건 처리</Text>
                    </div>
                  ),
                },
                {
                  color: 'green',
                  children: (
                    <div>
                      <Text strong>AI 분석 엔진 구축</Text>
                      <br />
                      <Text type="secondary">Gemini-2.5-Flash-Lite 모델 적용</Text>
                    </div>
                  ),
                },
                {
                  color: 'blue',
                  children: (
                    <div>
                      <Text strong>웹 인터페이스 개발</Text>
                      <br />
                      <Text type="secondary">Ant Design 기반 화이트 톤 UI</Text>
                    </div>
                  ),
                },
                {
                  color: 'gray',
                  children: (
                    <div>
                      <Text>향후 계획: 실시간 데이터 연동</Text>
                    </div>
                  ),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>

      {/* 시스템 정보 */}
      <Card title="시스템 정보" size="small">
        <Row gutter={[16, 8]}>
          <Col xs={24} sm={12} md={6}>
            <Text type="secondary">데이터 업데이트</Text>
            <br />
            <Text strong>2025-01-19</Text>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Text type="secondary">처리 모델</Text>
            <br />
            <Text strong>Gemini-2.5-Flash-Lite</Text>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Text type="secondary">데이터베이스</Text>
            <br />
            <Text strong>SQLite</Text>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Text type="secondary">응답 속도</Text>
            <br />
            <Text strong>평균 1.0초</Text>
          </Col>
        </Row>
      </Card>
    </div>
  );
}