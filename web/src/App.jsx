import React, { useState, useEffect, useCallback, useRef } from 'react';
import ReportViewer from './components/ReportViewer';
import SourceDataViewer from './components/SourceDataViewer';
import SentimentDashboard from './components/SentimentDashboard';
import DataSourceDashboard from './components/DataSourceDashboard';
import StockDiagnosis from './components/StockDiagnosis';
import IndexOverview from './components/IndexOverview';
import EconomicCalendar from './components/EconomicCalendar';
import HotConcepts from './components/HotConcepts';
import RiskAlerts from './components/RiskAlerts';
import DataSourceSelector from './components/DataSourceSelector';
import ChatAssistant from './components/ChatAssistant';
import USTechStocks from './components/USTechStocks';
import Watchlist from './components/Watchlist';
import { prefetchDashboardData } from './services/dataCache';
import {
  CalendarDays, CalendarRange, FileText, Activity, LogOut, RefreshCw,
  Play, BarChart, Radar, Stethoscope, LineChart, Flame, ShieldAlert,
  DollarSign, Star, ChevronDown, LayoutDashboard, Newspaper, Building2,
  Wrench
} from 'lucide-react';
import './Login.css';

/* ─── Navigation Structure ─── */
const NAV_GROUPS = [
  {
    key: 'overview',
    label: '概览',
    labelShort: '概览',
    icon: 'LayoutDashboard',
    items: [
      { key: 'watchlist', label: '自选股', labelShort: '自选', icon: 'Star' },
    ],
  },
  {
    key: 'reports',
    label: '报告',
    labelShort: '报告',
    icon: 'Newspaper',
    items: [
      { key: 'daily', label: '市场晨讯', labelShort: '晨讯', icon: 'FileText' },
      { key: 'weekly', label: '每周复盘', labelShort: '周报', icon: 'CalendarRange' },
      { key: 'radar', label: '全景雷达', labelShort: '雷达', icon: 'Radar' },
    ],
  },
  {
    key: 'ashare',
    label: 'A股',
    labelShort: 'A股',
    icon: 'Building2',
    items: [
      { key: 'sentiment', label: 'AI 情绪看板', labelShort: '情绪', icon: 'BarChart' },
      { key: 'index', label: '指数K线', labelShort: 'K线', icon: 'LineChart' },
      { key: 'concept', label: '热点题材', labelShort: '题材', icon: 'Flame' },
      { key: 'risk', label: '风险预警', labelShort: '风险', icon: 'ShieldAlert' },
    ],
  },
  {
    key: 'usmarket',
    label: '美股',
    labelShort: '美股',
    icon: 'DollarSign',
    items: [
      { key: 'ustech', label: '美股科技', labelShort: '科技', icon: 'DollarSign' },
    ],
  },
  {
    key: 'tools',
    label: '工具',
    labelShort: '工具',
    icon: 'Wrench',
    items: [
      { key: 'diagnosis', label: '个股诊断', labelShort: '诊断', icon: 'Stethoscope' },
      { key: 'calendar', label: '财经日历', labelShort: '日历', icon: 'CalendarDays' },
    ],
  },
];

/* ─── Icon Map ─── */
const ICON_MAP = {
  LayoutDashboard, Newspaper, Building2, DollarSign, Wrench,
  Star, FileText, CalendarRange, Radar, BarChart, LineChart,
  Flame, ShieldAlert, Stethoscope, CalendarDays,
};

const getIcon = (name, size = 18) => {
  const Icon = ICON_MAP[name];
  return Icon ? <Icon size={size} /> : null;
};

/* ─── Find which group a tab belongs to ─── */
const findGroupForTab = (tabKey) => {
  for (const group of NAV_GROUPS) {
    if (group.items.some(item => item.key === tabKey)) {
      return group.key;
    }
  }
  return NAV_GROUPS[0].key;
};

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return localStorage.getItem('auth_token') === 'valid_token';
  });
  const [loginUser, setLoginUser] = useState('');
  const [loginPass, setLoginPass] = useState('');
  const [loginError, setLoginError] = useState('');

  const [activeTab, setActiveTab] = useState('watchlist');
  const [expandedGroup, setExpandedGroup] = useState(() => findGroupForTab('watchlist'));
  const [viewMode, setViewMode] = useState('report');
  const [reports, setReports] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [currentReport, setCurrentReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [generating, setGenerating] = useState(false);

  // Sentiment State
  const [sentimentData, setSentimentData] = useState(null);
  const [sentimentLoading, setSentimentLoading] = useState(false);

  const mobileScrollRef = useRef(null);

  /* ─── Auto-scroll active mobile tab into view ─── */
  useEffect(() => {
    if (!mobileScrollRef.current) return;
    const active = mobileScrollRef.current.querySelector('.mobile-nav-item.active');
    if (active) {
      active.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
  }, [activeTab]);

  /* ─── Navigation Handlers ─── */
  const handleGroupClick = useCallback((groupKey) => {
    setExpandedGroup(prev => prev === groupKey ? null : groupKey);
  }, []);

  const handleTabClick = useCallback((tabKey, groupKey) => {
    setActiveTab(tabKey);
    setExpandedGroup(groupKey);
  }, []);

  /* ─── Auth ─── */
  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loginUser, password: loginPass })
      });

      if (response.ok) {
        localStorage.setItem('auth_token', 'valid_token');
        setIsAuthenticated(true);
        setLoginError('');
      } else {
        setLoginError('用户名或密码错误');
      }
    } catch (err) {
      setLoginError('登录服务不可用');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    setIsAuthenticated(false);
    setLoginUser('');
    setLoginPass('');
  };

  const handleGenerate = async () => {
    const isWeekly = activeTab === 'weekly';
    const endpoint = isWeekly ? '/api/trigger/weekly' : '/api/trigger/daily';
    const label = isWeekly ? '周报' : '晨报';

    if (!window.confirm(`确认要立即生成最新的【${label}】吗？\n\n生成过程可能需要 1-2 分钟，任务将在后台运行。`)) {
      return;
    }

    setGenerating(true);
    try {
      const res = await fetch(endpoint, { method: 'POST' });
      if (res.ok) {
        alert("🚀 生成任务已启动！\nAI 正在拼命撰写中，请过几分钟刷新页面查看最新报告。");
      } else {
        alert("❌ 触发失败，请检查服务状态。");
      }
    } catch (e) {
      alert("❌ 请求发送失败: " + e.message);
    } finally {
      setGenerating(false);
    }
  };

  /* ─── Data Loading ─── */
  useEffect(() => {
    if (!isAuthenticated) return;

    prefetchDashboardData();

    fetch('/api/reports')
      .then(res => res.json())
      .then(data => {
        setReports(data);
        selectLatestReport(data, activeTab);
      })
      .catch(err => console.error("Failed to list reports", err));

    setSentimentLoading(true);
    fetch('/api/sentiment')
      .then(res => res.json())
      .then(data => setSentimentData(data))
      .catch(err => console.error("Failed to fetch sentiment", err))
      .finally(() => setSentimentLoading(false));
  }, [isAuthenticated]);

  useEffect(() => {
    if (reports.length > 0) {
      selectLatestReport(reports, activeTab);
    }
  }, [activeTab]);

  const selectLatestReport = (allReports, type) => {
    const relevant = allReports.filter(r => r.type === type);
    if (relevant.length > 0) {
      fetchReport(relevant[0].date, type);
    } else {
      setCurrentReport(null);
      setSelectedDate('');
    }
  };

  const fetchReport = (date, type) => {
    setLoading(true);
    setError(null);
    setSelectedDate(date);

    fetch(`/api/reports/${date}?type=${type}`)
      .then(res => {
        if (!res.ok) throw new Error("Report not found");
        return res.json();
      })
      .then(data => {
        setCurrentReport(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  };

  const handleDateChange = (e) => {
    const newDate = e.target.value;
    fetchReport(newDate, activeTab);
  };

  const availableDates = reports
    .filter(r => r.type === activeTab)
    .map(r => r.date);

  /* ─── Login Screen ─── */
  if (!isAuthenticated) {
    return (
      <div className="login-container">
        <div className="login-card">
          <div className="sidebar-header" style={{ justifyContent: 'center', marginBottom: '20px' }}>
            <Activity color="#d32f2f" size={32} />
            <span style={{ fontSize: '1.5rem' }}>小红花</span>
          </div>
          <h2 className="login-title">请登录</h2>
          <form className="login-form" onSubmit={handleLogin}>
            <div className="form-group">
              <label>用户名</label>
              <input
                type="text"
                value={loginUser}
                onChange={(e) => setLoginUser(e.target.value)}
                placeholder="请输入用户名"
              />
            </div>
            <div className="form-group">
              <label>密码</label>
              <input
                type="password"
                value={loginPass}
                onChange={(e) => setLoginPass(e.target.value)}
                placeholder="请输入密码"
              />
            </div>
            {loginError && <div className="error-message">{loginError}</div>}
            <button type="submit" className="login-button">登录</button>
          </form>
        </div>
      </div>
    );
  }

  /* ─── Main Layout ─── */
  return (
    <div className="layout">
      {/* ── Sidebar (Desktop) ── */}
      <div className="sidebar">
        <div className="sidebar-header">
          <Activity color="#d32f2f" />
          <span>小红花</span>
        </div>

        <nav className="nav-groups">
          {NAV_GROUPS.map(group => {
            const isExpanded = expandedGroup === group.key;
            const hasActiveChild = group.items.some(item => item.key === activeTab);
            // Single-item groups: click goes directly to that tab
            const isSingleItem = group.items.length === 1;

            return (
              <div key={group.key} className={`nav-group ${isExpanded ? 'expanded' : ''} ${hasActiveChild ? 'has-active' : ''}`}>
                <div
                  className={`nav-group-header ${hasActiveChild ? 'active' : ''}`}
                  onClick={() => {
                    if (isSingleItem) {
                      handleTabClick(group.items[0].key, group.key);
                    } else {
                      handleGroupClick(group.key);
                    }
                  }}
                >
                  <div className="nav-group-label">
                    {getIcon(group.icon, 18)}
                    <span>{group.label}</span>
                  </div>
                  {!isSingleItem && (
                    <ChevronDown size={14} className={`nav-chevron ${isExpanded ? 'rotated' : ''}`} />
                  )}
                </div>

                {!isSingleItem && isExpanded && (
                  <div className="nav-group-items">
                    {group.items.map(item => (
                      <div
                        key={item.key}
                        className={`nav-item ${activeTab === item.key ? 'active' : ''}`}
                        onClick={() => handleTabClick(item.key, group.key)}
                        title={item.label}
                      >
                        {getIcon(item.icon, 16)}
                        <span>{item.label}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* Logout + Footer */}
        <div className="sidebar-bottom">
          <div
            className="nav-item logout-item"
            onClick={handleLogout}
            title="退出登录"
          >
            <LogOut size={18} />
            <span>退出登录</span>
          </div>
          <div className="sidebar-footer">
            <DataSourceSelector />
            <p>数据来源: AkShare</p>
            <p>生成时间: 08:00 AM</p>
          </div>
        </div>
      </div>

      {/* ── Mobile Nav ── */}
      <div className="mobile-nav">
        <div className="mobile-nav-header">
          <Activity color="#d32f2f" size={20} />
          <span className="mobile-brand">小红花</span>
          <div
            className="mobile-logout"
            onClick={handleLogout}
            title="退出登录"
          >
            <LogOut size={16} />
          </div>
        </div>
        {/* Row 1: 5 group tabs */}
        <div className="mobile-nav-groups" ref={mobileScrollRef}>
          {NAV_GROUPS.map(group => {
            const hasActiveChild = group.items.some(item => item.key === activeTab);
            const isSingleItem = group.items.length === 1;
            return (
              <div
                key={group.key}
                className={`mobile-group-tab ${hasActiveChild ? 'active' : ''}`}
                onClick={() => {
                  if (isSingleItem) {
                    handleTabClick(group.items[0].key, group.key);
                  } else {
                    // Toggle sub-items row; if clicking same group, close it
                    setExpandedGroup(prev => prev === group.key ? null : group.key);
                    // If no child is active yet, select first child
                    if (!hasActiveChild) {
                      handleTabClick(group.items[0].key, group.key);
                    }
                  }
                }}
              >
                {getIcon(group.icon, 16)}
                <span>{group.labelShort}</span>
              </div>
            );
          })}
        </div>
        {/* Row 2: Sub-items of expanded group (only for multi-item groups) */}
        {NAV_GROUPS.map(group => {
          if (group.items.length <= 1) return null;
          const hasActiveChild = group.items.some(item => item.key === activeTab);
          if (!hasActiveChild && expandedGroup !== group.key) return null;
          if (!hasActiveChild && expandedGroup === group.key) {
            // Show if group is expanded
          } else if (hasActiveChild) {
            // Always show sub-row when a child is active
          } else {
            return null;
          }
          return (
            <div key={group.key} className="mobile-sub-row">
              {group.items.map(item => (
                <div
                  key={item.key}
                  className={`mobile-sub-item ${activeTab === item.key ? 'active' : ''}`}
                  onClick={() => handleTabClick(item.key, group.key)}
                >
                  <span>{item.labelShort}</span>
                </div>
              ))}
            </div>
          );
        })}
      </div>

      {/* ── Main Content ── */}
      <div className="main-content">
        {activeTab === 'watchlist' && <Watchlist />}

        {activeTab === 'sentiment' && (
          <SentimentDashboard data={sentimentData} loading={sentimentLoading} />
        )}

        {activeTab === 'radar' && <DataSourceDashboard />}
        {activeTab === 'diagnosis' && <StockDiagnosis />}
        {activeTab === 'index' && <IndexOverview />}
        {activeTab === 'calendar' && <EconomicCalendar />}
        {activeTab === 'concept' && <HotConcepts />}
        {activeTab === 'risk' && <RiskAlerts />}
        {activeTab === 'ustech' && <USTechStocks />}

        {(activeTab === 'daily' || activeTab === 'weekly') && (
          <>
            <div className="report-controls">
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <label>选择日期: </label>
                <select
                  className="date-selector"
                  value={selectedDate}
                  onChange={handleDateChange}
                  disabled={availableDates.length === 0}
                >
                  {availableDates.map(date => (
                    <option key={date} value={date}>{date}</option>
                  ))}
                  {availableDates.length === 0 && <option>无数据</option>}
                </select>
              </div>

              <div className="view-tabs">
                <div
                  className={`view-tab ${viewMode === 'report' ? 'active' : ''}`}
                  onClick={() => setViewMode('report')}
                >
                  正文 Briefing
                </div>
                <div
                  className={`view-tab ${viewMode === 'source' ? 'active' : ''}`}
                  onClick={() => setViewMode('source')}
                >
                  数据源 Source Data
                </div>
              </div>

              <button
                onClick={handleGenerate}
                disabled={generating}
                style={{
                  marginLeft: 'auto',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  borderRadius: '6px',
                  border: 'none',
                  backgroundColor: generating ? '#e0e0e0' : '#d32f2f',
                  color: 'white',
                  cursor: generating ? 'not-allowed' : 'pointer',
                  fontSize: '14px',
                  fontWeight: '500',
                  transition: 'background-color 0.2s'
                }}
              >
                {generating ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} fill="white" />}
                {generating ? '生成中...' : `生成${activeTab === 'weekly' ? '周报' : '日报'}`}
              </button>
            </div>

            {loading && <div className="loading">加载中...</div>}
            {error && <div className="error">加载失败: {error}</div>}

            {!loading && !error && currentReport && viewMode === 'report' && (
              <div className="report-card">
                <ReportViewer htmlContent={currentReport.content_html} />
              </div>
            )}

            {!loading && !error && currentReport && viewMode === 'source' && (
              <div className="source-view-card">
                <div className="source-header">
                  <Activity size={16} /> 原始数据来源
                </div>
                <div className="source-content">
                  <SourceDataViewer rawData={currentReport.raw_data} />
                </div>
              </div>
            )}

            {!loading && !error && !currentReport && (
              <div className="empty">暂无报告数据</div>
            )}
          </>
        )}
      </div>

      {/* AI Chat Assistant - Available on all pages */}
      {isAuthenticated && <ChatAssistant />}
    </div>
  );
}

export default App;
