import React, { useState, useEffect, useMemo } from 'react';
import { Radar, RefreshCw, Calendar, FileText } from 'lucide-react';
import { parseRawData } from '../utils/parseRawData';
import MarketOverviewCard from './datasource/MarketOverviewCard';
import TurnoverCard from './datasource/TurnoverCard';
import SentimentMiniCard from './datasource/SentimentMiniCard';
import SectorPerformance from './datasource/SectorPerformance';
import NewsSection from './datasource/NewsSection';
import LimitUpLadderEnhanced from './datasource/LimitUpLadderEnhanced';
import './DataSourceDashboard.css';

/**
 * Data Source Dashboard - displays parsed data from daily/weekly reports
 * Replaces the old MarketRadar component
 */
const DataSourceDashboard = () => {
  const [activeTab, setActiveTab] = useState('daily');
  const [reports, setReports] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [currentReport, setCurrentReport] = useState(null);
  const [sentiment, setSentiment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch available reports list on mount
  useEffect(() => {
    fetch('/api/reports')
      .then(res => res.json())
      .then(data => {
        setReports(data);
        selectLatestReport(data, activeTab);
      })
      .catch(err => {
        console.error('Failed to fetch reports:', err);
        setError('无法加载报告列表');
        setLoading(false);
      });

    // Fetch sentiment data
    fetch('/api/sentiment')
      .then(res => res.json())
      .then(data => setSentiment(data))
      .catch(err => console.error('Failed to fetch sentiment:', err));
  }, []);

  // When tab changes, select latest report of that type
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
      setLoading(false);
    }
  };

  const fetchReport = async (date, type) => {
    setLoading(true);
    setError(null);
    setSelectedDate(date);

    try {
      const res = await fetch(`/api/reports/${date}?type=${type}`);
      if (!res.ok) throw new Error('Report not found');
      const data = await res.json();
      setCurrentReport(data);
    } catch (err) {
      setError(err.message);
      setCurrentReport(null);
    } finally {
      setLoading(false);
    }
  };

  const handleDateChange = (e) => {
    const newDate = e.target.value;
    if (newDate) {
      fetchReport(newDate, activeTab);
    }
  };

  const handleRefresh = () => {
    if (selectedDate) {
      fetchReport(selectedDate, activeTab);
    }
  };

  // Filter available dates for current tab
  const availableDates = useMemo(() => {
    return reports
      .filter(r => r.type === activeTab)
      .map(r => r.date);
  }, [reports, activeTab]);

  // Parse the raw data
  const parsedData = useMemo(() => {
    if (!currentReport || !currentReport.raw_data) {
      return null;
    }
    // Merge report's sentiment if available, otherwise use fetched sentiment
    const reportSentiment = currentReport.sentiment || sentiment;
    return parseRawData(currentReport.raw_data, reportSentiment);
  }, [currentReport, sentiment]);

  // Skeleton loading component
  const SkeletonCard = ({ height = '200px' }) => (
    <div className="ds-card skeleton-card" style={{ minHeight: height }}>
      <div className="skeleton-title"></div>
      <div className="skeleton-content">
        <div className="skeleton-row"></div>
        <div className="skeleton-row"></div>
        <div className="skeleton-row short"></div>
      </div>
    </div>
  );

  return (
    <div className="data-source-dashboard">
      {/* Header */}
      <div className="ds-header">
        <div className="ds-title">
          <Radar className="text-red-600" size={28} />
          <span>全景雷达 (Data Source)</span>
        </div>
        <div className="ds-controls">
          {/* Date Selector */}
          <select
            className="ds-date-selector"
            value={selectedDate}
            onChange={handleDateChange}
            disabled={availableDates.length === 0 || loading}
          >
            {availableDates.map(date => (
              <option key={date} value={date}>{date}</option>
            ))}
            {availableDates.length === 0 && <option>无数据</option>}
          </select>
          {/* Refresh Button */}
          <button
            className="ds-refresh-btn"
            onClick={handleRefresh}
            disabled={loading}
            title="刷新数据"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="ds-tabs">
        <button
          className={`ds-tab ${activeTab === 'daily' ? 'active' : ''}`}
          onClick={() => setActiveTab('daily')}
        >
          <FileText size={16} />
          <span>市场晨讯 (Daily)</span>
        </button>
        <button
          className={`ds-tab ${activeTab === 'weekly' ? 'active' : ''}`}
          onClick={() => setActiveTab('weekly')}
        >
          <Calendar size={16} />
          <span>每周复盘 (Weekly)</span>
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="ds-content">
          <div className="ds-top-row">
            <SkeletonCard height="160px" />
            <SkeletonCard height="160px" />
            <SkeletonCard height="160px" />
          </div>
          <SkeletonCard height="200px" />
          <SkeletonCard height="150px" />
          <SkeletonCard height="300px" />
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="ds-error">
          <span>加载失败: {error}</span>
          <button onClick={handleRefresh}>重试</button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && !parsedData && (
        <div className="ds-empty">
          <Radar size={48} className="text-gray-300" />
          <p>暂无 {activeTab === 'daily' ? '晨讯' : '周报'} 数据</p>
          <p className="hint">请等待系统生成报告或手动触发生成</p>
        </div>
      )}

      {/* Data Display */}
      {!loading && !error && parsedData && (
        <div className="ds-content">
          {/* Top Row - Overview Cards */}
          <div className="ds-top-row">
            <MarketOverviewCard data={parsedData.marketOverview} />
            <TurnoverCard
              turnover={parsedData.turnover}
              turnoverChange={parsedData.turnoverChange}
            />
            <SentimentMiniCard sentiment={parsedData.sentiment} />
          </div>

          {/* Sector Performance */}
          <SectorPerformance sectors={parsedData.sectors} />

          {/* News Section */}
          <NewsSection news={parsedData.news} />

          {/* Limit-Up Ladder */}
          <LimitUpLadderEnhanced ladder={parsedData.ladder} />

          {/* Footer - Data Source Info */}
          <div className="ds-footer">
            <span>数据来源: {currentReport?.date} {activeTab === 'daily' ? '晨报' : '周报'}</span>
            <span>生成时间: {currentReport?.created_at ? new Date(currentReport.created_at).toLocaleString('zh-CN') : '-'}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default DataSourceDashboard;
