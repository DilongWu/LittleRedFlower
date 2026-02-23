import React, { useState, useEffect } from 'react';
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
import { CalendarDays, CalendarRange, FileText, Activity, LogOut, RefreshCw, Play, BarChart, Radar, Stethoscope, LineChart, Flame, ShieldAlert, DollarSign, Star } from 'lucide-react';
import './Login.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return localStorage.getItem('auth_token') === 'valid_token';
  });
  const [loginUser, setLoginUser] = useState('');
  const [loginPass, setLoginPass] = useState('');
  const [loginError, setLoginError] = useState('');

  const [activeTab, setActiveTab] = useState('daily');
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

  // Load available reports list on mount or auth change
  useEffect(() => {
    if (!isAuthenticated) return;

    // Prefetch all dashboard data in background for faster tab switching
    prefetchDashboardData();

    // Fetch reports
    fetch('/api/reports')
      .then(res => res.json())
      .then(data => {
        setReports(data);
        selectLatestReport(data, activeTab);
      })
      .catch(err => console.error("Failed to list reports", err));

    // Fetch Sentiment
    setSentimentLoading(true);
    fetch('/api/sentiment')
      .then(res => res.json())
      .then(data => setSentimentData(data))
      .catch(err => console.error("Failed to fetch sentiment", err))
      .finally(() => setSentimentLoading(false));

  }, [isAuthenticated]);

  // When tab changes, find relevant report
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

  // Filter available dates for current tab
  const availableDates = reports
    .filter(r => r.type === activeTab)
    .map(r => r.date);

  if (!isAuthenticated) {
    return (
      <div className="login-container">
        <div className="login-card">
          <div className="sidebar-header" style={{justifyContent: 'center', marginBottom: '20px'}}>
             <Activity color="#d32f2f" size={32} />
             <span style={{fontSize: '1.5rem'}}>小红花</span>
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

  return (
    <div className="layout">
      <div className="sidebar">
        <div className="sidebar-header">
          <Activity color="#d32f2f" />
          <span>小红花</span>
        </div>

        <div className="mobile-nav-scroll">
          <div
            className={`nav-item ${activeTab === 'watchlist' ? 'active' : ''}`}
            onClick={() => setActiveTab('watchlist')}
            title="自选股"
          >
            <Star size={18} />
            <span className="nav-label-full">自选股 (Watchlist)</span>
            <span className="nav-label-short">自选</span>
          </div>

          <div
            className={`nav-item ${activeTab === 'daily' ? 'active' : ''}`}
            onClick={() => setActiveTab('daily')}
            title="市场晨讯"
          >
            <FileText size={18} />
            <span className="nav-label-full">市场晨讯 (Daily)</span>
            <span className="nav-label-short">晨讯</span>
          </div>

          <div
            className={`nav-item ${activeTab === 'weekly' ? 'active' : ''}`}
            onClick={() => setActiveTab('weekly')}
            title="每周复盘"
          >
            <CalendarRange size={18} />
            <span className="nav-label-full">每周复盘 (Weekly)</span>
            <span className="nav-label-short">周报</span>
          </div>

          <div
            className={`nav-item ${activeTab === 'sentiment' ? 'active' : ''}`}
            onClick={() => setActiveTab('sentiment')}
            title="AI 情绪看板"
          >
            <BarChart size={18} />
            <span className="nav-label-full">AI 情绪看板 (Sentiment)</span>
            <span className="nav-label-short">情绪</span>
          </div>

          <div
            className={`nav-item ${activeTab === 'radar' ? 'active' : ''}`}
            onClick={() => setActiveTab('radar')}
            title="全景雷达"
          >
            <Radar size={18} />
            <span className="nav-label-full">全景雷达 (Radar)</span>
            <span className="nav-label-short">雷达</span>
          </div>

          <div
            className={`nav-item ${activeTab === 'index' ? 'active' : ''}`}
            onClick={() => setActiveTab('index')}
            title="指数K线"
          >
            <LineChart size={18} />
            <span className="nav-label-full">指数K线 (Index)</span>
            <span className="nav-label-short">K线</span>
          </div>

          <div
            className={`nav-item ${activeTab === 'diagnosis' ? 'active' : ''}`}
            onClick={() => setActiveTab('diagnosis')}
            title="个股诊断"
          >
            <Stethoscope size={18} />
            <span className="nav-label-full">个股诊断 (Diagnosis)</span>
            <span className="nav-label-short">诊断</span>
          </div>

          <div
            className={`nav-item ${activeTab === 'calendar' ? 'active' : ''}`}
            onClick={() => setActiveTab('calendar')}
            title="财经日历"
          >
            <CalendarDays size={18} />
            <span className="nav-label-full">财经日历 (Calendar)</span>
            <span className="nav-label-short">日历</span>
          </div>

          <div
            className={`nav-item ${activeTab === 'concept' ? 'active' : ''}`}
            onClick={() => setActiveTab('concept')}
            title="热点题材"
          >
            <Flame size={18} />
            <span className="nav-label-full">热点题材 (Themes)</span>
            <span className="nav-label-short">题材</span>
          </div>

          <div
            className={`nav-item ${activeTab === 'risk' ? 'active' : ''}`}
            onClick={() => setActiveTab('risk')}
            title="风险预警"
          >
            <ShieldAlert size={18} />
            <span className="nav-label-full">风险预警 (Risk)</span>
            <span className="nav-label-short">风险</span>
          </div>

          <div
            className={`nav-item ${activeTab === 'ustech' ? 'active' : ''}`}
            onClick={() => setActiveTab('ustech')}
            title="美股科技"
          >
            <DollarSign size={18} />
            <span className="nav-label-full">美股科技 (US Tech)</span>
            <span className="nav-label-short">美股</span>
          </div>

          <div
             className="nav-item"
             onClick={handleLogout}
             style={{color: '#d32f2f'}}
             title="退出登录"
          >
            <LogOut size={18} />
            <span>退出登录</span>
          </div>
        </div>

        <div className="sidebar-footer" style={{ marginTop: 'auto', fontSize: '0.8rem', color: '#888' }}>
          <div style={{ position: 'relative', marginBottom: '15px' }}>
            <DataSourceSelector />
          </div>
          <p>数据来源: AkShare</p>
          <p>生成时间: 08:00 AM</p>
        </div>
      </div>

      <div className="main-content">
        {activeTab === 'watchlist' && (
          <Watchlist />
        )}

        {activeTab === 'sentiment' && (
           <SentimentDashboard data={sentimentData} loading={sentimentLoading} />
        )}

          {activeTab === 'radar' && (
            <DataSourceDashboard />
          )}

          {activeTab === 'diagnosis' ? (
            <StockDiagnosis />
          ) : null}

          {activeTab === 'index' ? (
            <IndexOverview />
          ) : null}

          {activeTab === 'calendar' ? (
            <EconomicCalendar />
          ) : null}

          {activeTab === 'concept' ? (
            <HotConcepts />
          ) : null}

          {activeTab === 'risk' ? (
            <RiskAlerts />
          ) : null}

          {activeTab === 'ustech' ? (
            <USTechStocks />
          ) : null}

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
