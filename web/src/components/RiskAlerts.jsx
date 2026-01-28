import React, { useEffect, useState } from 'react';
import { AlertTriangle, RefreshCw, ShieldAlert } from 'lucide-react';
import { fetchWithCache, API_ENDPOINTS } from '../services/dataCache';
import './RiskAlerts.css';

const buildAlerts = (sentiment, indexes) => {
  const alerts = [];

  if (sentiment?.score !== undefined) {
    if (sentiment.score >= 80) {
      alerts.push({ level: 'high', text: '市场情绪过热，注意追高风险。' });
    } else if (sentiment.score <= 20) {
      alerts.push({ level: 'high', text: '市场情绪极度低迷，谨防恐慌踩踏。' });
    } else if (sentiment.score <= 35) {
      alerts.push({ level: 'medium', text: '情绪偏冷，控制仓位、降低节奏。' });
    }
  }

  if (Array.isArray(indexes)) {
    indexes.forEach(idx => {
      if (idx.change_pct <= -2) {
        alerts.push({ level: 'high', text: `${idx.name} 单日跌幅较大，注意系统性风险。` });
      }
      if (idx.close && idx.ma20 && idx.close < idx.ma20) {
        alerts.push({ level: 'medium', text: `${idx.name} 跌破20日均线，短线偏弱。` });
      }
    });
  }

  if (alerts.length === 0) {
    alerts.push({ level: 'low', text: '暂无明显风险信号。' });
  }

  return alerts;
};

// Skeleton loading
const SkeletonAlerts = () => (
  <>
    {[1, 2, 3].map(i => (
      <div key={i} className="risk-item skeleton-risk-item">
        <div className="skeleton-risk-icon"></div>
        <div className="skeleton-risk-text"></div>
      </div>
    ))}
  </>
);

const RiskAlerts = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      let sentiment, indexes;

      if (forceRefresh) {
        const [sentimentRes, indexRes] = await Promise.all([
          fetch(API_ENDPOINTS.SENTIMENT),
          fetch(API_ENDPOINTS.INDEX_OVERVIEW)
        ]);

        if (!sentimentRes.ok || !indexRes.ok) {
          throw new Error('无法获取风险数据');
        }

        sentiment = await sentimentRes.json();
        indexes = await indexRes.json();
      } else {
        [sentiment, indexes] = await Promise.all([
          fetchWithCache(API_ENDPOINTS.SENTIMENT),
          fetchWithCache(API_ENDPOINTS.INDEX_OVERVIEW)
        ]);
      }

      setAlerts(buildAlerts(sentiment, indexes));
    } catch (e) {
      setError(e.message);
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="risk-page">
      <div className="risk-header">
        <div className="risk-title">
          <ShieldAlert size={22} className="text-yellow-600" />
          风险预警
        </div>
        <button onClick={() => fetchData(true)} className="risk-refresh" disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          刷新
        </button>
      </div>

      {error ? <div className="risk-error">{error}</div> : null}

      <div className="risk-list">
        {loading && alerts.length === 0 ? (
          <SkeletonAlerts />
        ) : (
          alerts.map((a, idx) => (
            <div key={`${a.text}-${idx}`} className={`risk-item ${a.level}`}>
              <AlertTriangle size={16} />
              <span>{a.text}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default RiskAlerts;
