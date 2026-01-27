import React, { useEffect, useState } from 'react';
import { AlertTriangle, RefreshCw, ShieldAlert } from 'lucide-react';
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

const RiskAlerts = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sentimentRes, indexRes] = await Promise.all([
        fetch('/api/sentiment'),
        fetch('/api/index/overview')
      ]);

      if (!sentimentRes.ok || !indexRes.ok) {
        throw new Error('无法获取风险数据');
      }

      const sentiment = await sentimentRes.json();
      const indexes = await indexRes.json();
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
        <button onClick={fetchData} className="risk-refresh" disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          刷新
        </button>
      </div>

      {error ? <div className="risk-error">{error}</div> : null}

      <div className="risk-list">
        {alerts.map((a, idx) => (
          <div key={`${a.text}-${idx}`} className={`risk-item ${a.level}`}>
            <AlertTriangle size={16} />
            <span>{a.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RiskAlerts;
