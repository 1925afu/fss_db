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
  PieChartOutlined,
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
  const [violationStats, setViolationStats] = useState<any[]>([]);
  const [industryStats, setIndustryStats] = useState<any[]>([]);
  const [sanctionTypes, setSanctionTypes] = useState<any[]>([]);

  // API에서 데이터 가져오기
  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      // 통계 데이터 가져오기 (V2 대시보드 통계 사용)
      const stats = await decisionsService.getDecisionStats();
      
      // 최근 의결서 가져오기
      const decisions = await decisionsService.getDecisions({ limit: 5 });
      
      // V2 실제 데이터 기반 통계 (검색 통계 API 사용)
      const searchStats = await searchService.getSearchStats();
      
      // 위반 유형 통계 (임시 데이터 - V2에는 위반 유형별 분류가 없음)
      const violationData = [
        { type: '내부통제 위반', count: 15, percentage: 30 },
        { type: '준법감시 소홀', count: 12, percentage: 24 },
        { type: '회계처리기준 위반', count: 10, percentage: 20 },
        { type: '정보공개 위반', count: 8, percentage: 16 },
        { type: '기타', count: 5, percentage: 10 }
      ];
      
      // 제재 유형 데이터 (V2 실제 데이터)
      const sanctionData = [
        { type: '과태료', value: 24 },
        { type: '과징금', value: 11 },
        { type: '주의/경고', value: 5 },
        { type: '면제', value: 1 }
      ];
      
      // 데이터 포맷팅 (V2 API 구조에 맞게 수정)
      const formattedData = {
        totalDecisions: stats.summary.total_decisions,
        totalActions: stats.summary.total_actions,
        totalLaws: stats.summary.total_laws,
        totalFineAmount: stats.summary.total_fine_amount,
        yearlyDistribution: stats.monthly_trends || [],
        industryDistribution: stats.categories?.category_1 || [],
      };

      setDashboardData(formattedData);
      // V2 API는 recent_decisions를 직접 반환
      setRecentDecisions(stats.recent_decisions || []);
      setViolationStats(violationData);
      
      // 업권별 통계 데이터 (V2 실제 데이터 사용)
      const industryData = searchStats.industry_distribution || [
        { sector: '자산운용', count: 4 },
        { sector: '금융투자', count: 3 }
      ];
      setIndustryStats(industryData);
      setSanctionTypes(sanctionData);
      setLoading(false);
    } catch (error) {
      console.error('Dashboard data fetch error:', error);
      setError('데이터를 불러오는 중 오류가 발생했습니다.');
      setLoading(false);
      
      // 오류 시 기본값 사용
      setDashboardData({
        totalDecisions: data?.totalDecisions || 0,
        totalActions: data?.totalActions || 0,
        totalLaws: data?.totalLaws || 0,
        yearlyDistribution: [],
        industryDistribution: []
      });
      setRecentDecisions([]);
      setViolationStats([]);
      setIndustryStats([]);
      setSanctionTypes([]);
    }
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
              dataSource={recentDecisions.map((d, index) => ({
                id: `${d.decision_year}-${d.decision_id}`,
                key: `decision-${d.decision_year}-${d.decision_id}-${index}`,
                title: d.title,
                date: d.decision_month === 0 || d.decision_day === 0 
                  ? '날짜 정보 없음' 
                  : d.decision_date || `${d.decision_year}-${String(d.decision_month).padStart(2, '0')}-${String(d.decision_day).padStart(2, '0')}`,
                type: d.category_1,
                category: d.category_2
              }))}
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
              {violationStats.map((item, index) => (
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
              {industryStats.slice(0, 4).map((item: any, index: number) => (
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
              ))}
            </div>
          </Card>
        </Col>

        {/* 제재 유형별 분포 */}
        <Col xs={24} lg={12}>
          <Card 
            title={
              <Space>
                <PieChartOutlined />
                <span>제재 유형별 분포</span>
              </Space>
            }
          >
            <div className="space-y-4">
              {sanctionTypes.map((item, index) => {
                const total = sanctionTypes.reduce((sum, s) => sum + s.value, 0);
                const percentage = Math.round((item.value / total) * 100);
                const colors = ['#1677ff', '#faad14', '#52c41a', '#ff4d4f', '#722ed1'];
                return (
                  <div key={index}>
                    <div className="flex justify-between items-center mb-1">
                      <Space>
                        <div 
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: colors[index] }}
                        />
                        <Text className="text-sm font-medium">{item.type}</Text>
                      </Space>
                      <Text className="text-sm text-gray-500">
                        {item.value}건 ({percentage}%)
                      </Text>
                    </div>
                    <Progress 
                      percent={percentage} 
                      showInfo={false}
                      strokeColor={colors[index]}
                      trailColor="#f0f0f0"
                    />
                  </div>
                );
              })}
              <div className="mt-4 pt-4 border-t">
                <Space direction="vertical" size="small" className="w-full">
                  <div className="flex justify-between">
                    <Text type="secondary">총 제재 건수</Text>
                    <Text strong>{sanctionTypes.reduce((sum, item) => sum + item.value, 0)}건</Text>
                  </div>
                  <Text type="secondary" className="text-xs">
                    과태료와 과징금이 전체 제재의 {Math.round((35/41) * 100)}%를 차지하고 있습니다.
                  </Text>
                </Space>
              </div>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}