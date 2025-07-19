'use client';

import React from 'react';
import { ConfigProvider, theme } from 'antd';
import koKR from 'antd/locale/ko_KR';
import { AntdRegistry } from '@ant-design/nextjs-registry';

const { defaultAlgorithm } = theme;

const whiteTheme = {
  token: {
    // 기본 색상 - 화이트 톤
    colorPrimary: '#1677ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#1677ff',
    
    // 배경색 - 매우 밝은 화이트 톤
    colorBgContainer: '#ffffff',
    colorBgElevated: '#ffffff',
    colorBgLayout: '#fafafa',
    colorBgSpotlight: '#ffffff',
    
    // 텍스트 색상
    colorText: '#262626',
    colorTextSecondary: '#595959',
    colorTextTertiary: '#8c8c8c',
    colorTextQuaternary: '#bfbfbf',
    
    // 테두리 색상 - 매우 연한 그레이
    colorBorder: '#f0f0f0',
    colorBorderSecondary: '#f5f5f5',
    
    // 폰트 설정
    fontFamily: 'var(--font-noto-sans-kr), -apple-system, BlinkMacSystemFont, sans-serif',
    fontSize: 14,
    fontSizeHeading1: 38,
    fontSizeHeading2: 30,
    fontSizeHeading3: 24,
    fontSizeHeading4: 20,
    fontSizeHeading5: 16,
    fontSizeIcon: 12,
    
    // 여백 및 크기
    sizeStep: 4,
    sizeUnit: 4,
    borderRadius: 6,
    borderRadiusLG: 8,
    borderRadiusSM: 4,
    borderRadiusXS: 2,
    
    // 그림자 - 매우 연한 그림자
    boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02)',
    boxShadowSecondary: '0 6px 16px 0 rgba(0, 0, 0, 0.08), 0 3px 6px -4px rgba(0, 0, 0, 0.12), 0 9px 28px 8px rgba(0, 0, 0, 0.05)',
  },
  components: {
    Layout: {
      headerBg: '#ffffff',
      bodyBg: '#fafafa',
      siderBg: '#ffffff',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#e6f4ff',
      itemHoverBg: '#f5f5f5',
      itemActiveBg: '#f0f0f0',
    },
    Card: {
      colorBgContainer: '#ffffff',
      colorBorderSecondary: '#f0f0f0',
    },
    Table: {
      headerBg: '#fafafa',
      headerColor: '#262626',
      rowHoverBg: '#fafafa',
    },
    Input: {
      colorBgContainer: '#ffffff',
      activeBorderColor: '#1677ff',
      hoverBorderColor: '#4096ff',
    },
    Button: {
      primaryShadow: '0 2px 0 rgba(5, 145, 255, 0.1)',
      colorPrimaryHover: '#4096ff',
      colorPrimaryActive: '#0958d9',
    },
  },
};

interface AntdProviderProps {
  children: React.ReactNode;
}

export default function AntdProvider({ children }: AntdProviderProps) {
  return (
    <AntdRegistry>
      <ConfigProvider
        locale={koKR}
        theme={whiteTheme}
        componentSize="middle"
      >
        {children}
      </ConfigProvider>
    </AntdRegistry>
  );
}