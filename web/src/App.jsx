import React, { useState, useEffect } from 'react';
import ReportViewer from './components/ReportViewer';
import SourceDataViewer from './components/SourceDataViewer';
import { Calendar, FileText, Activity, LogOut } from 'lucide-react';
import './Login.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return localStorage.getItem('auth_token') === 'valid_token';
  });
  const [loginUser, setLoginUser] = useState('');
  const [loginPass, setLoginPass] = useState('');
  const [loginError, setLoginError] = useState('');

  const [activeTab, setActiveTab] = useState('daily');
  const [viewMode, setViewMode] = useState('report'); // 'report' or 'source'
  const [reports, setReports] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [currentReport, setCurrentReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleLogin = (e) => {
    e.preventDefault();
    if (loginUser === 'admin' && loginPass === 'littleredfloweradmin') {
      localStorage.setItem('auth_token', 'valid_token');
      setIsAuthenticated(true);
      setLoginError('');
    } else {
      setLoginError('用户名或密码错误');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    setIsAuthenticated(false);
    setLoginUser('');
    setLoginPass('');
  };

  // Load available reports list on mount
  useEffect(() => {
    if (!isAuthenticated) return;
    
    fetch('/api/reports')
      .then(res => res.json())
      .then(data => {
        setReports(data);
        // Find latest report for current tab
        selectLatestReport(data, activeTab);
      })
      .catch(err => console.error("Failed to list reports", err));
  }, []);

  // When tab changes, find relevant report
  useEffect(() => {
    if (reports.length > 0) {
      selectLatestReport(reports, activeTab);
    }
  }, [activeTab]);

  const selectLatestReport = (allReports, type) => {
    const relevant = allReports.filter(r => r.type === type);
    if (relevant.length > 0) {
      // Assuming sorted desc
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
             <span style={{fontSize: '1.5rem'}}>睿组合小红花</span>
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
          <span>睿组合小红花</span>
        </div>
        
        <div 
          className={`nav-item ${activeTab === 'daily' ? 'active' : ''}`}
          onClick={() => setActiveTab('daily')}
        >
          <FileText size={18} />
          <span>市场晨讯 (Daily)</span>
        </div>
        
        <div 
          className={`nav-item ${activeTab === 'weekly' ? 'active' : ''}`}
          onClick={() => setActiveTab('weekly')}
        >
          <Calendar size={18} />
          <span>每周复盘 (Weekly)</span>
        </div>

        <div style={{ marginTop: 'auto', fontSize: '0.8rem', color: '#888' }}>
          <div 
             className="nav-item" 
             onClick={handleLogout}
             style={{color: '#d32f2f', marginBottom: '10px'}}
          >
            <LogOut size={18} />
            <span>退出登录</span>
          </div>
          <p>生成时间: 08:00 AM</p>
        </div>
      </div>

      <div className="main-content">
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
      </div>
    </div>
  );
}

export default App;
