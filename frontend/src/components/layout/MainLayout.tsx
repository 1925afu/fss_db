'use client';

import React from 'react';
import { Layout, Typography, Menu, Space } from 'antd';
import { 
  HomeOutlined, 
  SearchOutlined, 
  BarChartOutlined, 
  SettingOutlined,
  BookOutlined 
} from '@ant-design/icons';

const { Header, Content, Footer } = Layout;
const { Title } = Typography;

interface MainLayoutProps {
  children: React.ReactNode;
}

export default function MainLayout({ children }: MainLayoutProps) {
  const menuItems = [
    {
      key: 'home',
      icon: <HomeOutlined />,
      label: '홈',
    },
    {
      key: 'search',
      icon: <SearchOutlined />,
      label: '검색',
    },
    {
      key: 'analytics',
      icon: <BarChartOutlined />,
      label: '분석',
    },
    {
      key: 'laws',
      icon: <BookOutlined />,
      label: '법령',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '설정',
    },
  ];

  return (
    <Layout className="min-h-screen">
      <Header className="flex items-center justify-between px-6">
        <div className="flex items-center space-x-4">
          <Title level={3} className="!mb-0 !text-white">
            FSS 규제 인텔리전스
          </Title>
        </div>
        
        <Menu
          mode="horizontal"
          defaultSelectedKeys={['home']}
          items={menuItems}
          className="bg-transparent border-0 flex-1 justify-end"
          theme="light"
          style={{ 
            backgroundColor: 'transparent',
            borderBottom: 'none',
            color: '#262626'
          }}
        />
      </Header>

      <Content className="px-6 py-8">
        <div className="max-w-7xl mx-auto">
          {children}
        </div>
      </Content>

      <Footer className="text-center bg-white border-t border-gray-100">
        <Space direction="vertical" size={4}>
          <div>FSS 규제 인텔리전스 플랫폼 ©2025</div>
          <div className="text-gray-500 text-sm">
            금융위원회 의결서 검색 및 분석 시스템 | AI 기반 자연어 쿼리 지원
          </div>
        </Space>
      </Footer>
    </Layout>
  );
}