import React, { useEffect, useMemo, useState } from 'react';
import { TrendingUp, RefreshCw } from 'lucide-react';
import './IndexOverview.css';

const Sparkline = ({ series, up }) => {
  const points = useMemo(() => {
    if (!series || series.length === 0) return '';
    const max = Math.max(...series);
    const min = Math.min(...series);
    const range = max - min || 1;
    const width = 160;
    const height = 40;
    return series
      .map((v, i) => {
        const x = (i / (series.length - 1)) * width;
        const y = height - ((v - min) / range) * height;
        return `${x},${y}`;
      })
      .join(' ');
  }, [series]);

  return (
    <svg width="160" height="40" className="sparkline">
      <polyline
        fill="none"
        stroke={up ? '#ef4444' : '#16a34a'}
        strokeWidth="2"
        points={points}
      />
    </svg>
  );
};

const IndexOverview = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/index/overview');
      if (!res.ok) throw new Error('无法获取指数数据');
      const json = await res.json();
      setData(json || []);
    } catch (e) {
      setError(e.message);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="index-page">
      <div className="index-header">
        <div className="index-title">
          <TrendingUp size={22} className="text-red-600" />
          指数K线速览
        </div>
        <button onClick={fetchData} className="index-refresh" disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          刷新
        </button>
      </div>

      {error ? (
        <div className="index-error">{error}</div>
      ) : null}

      {data.length > 0 ? (
        <div className="index-grid">
          {data.map(item => (
            <div key={item.symbol} className="index-card">
              <div className="index-card-title">
                {item.name}
                <span className="index-symbol">{item.symbol}</span>
              </div>
              <div className="index-row">
                <div className="index-price">{item.close}</div>
                <div className={item.change_pct >= 0 ? 'index-change up' : 'index-change down'}>
                  {item.change_pct >= 0 ? '+' : ''}{item.change_pct}%
                </div>
              </div>
              <Sparkline series={item.series} up={item.change_pct >= 0} />
              <div className="index-ma">
                MA5: {item.ma5 ?? '-'} | MA20: {item.ma20 ?? '-'}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="index-empty">暂无指数数据</div>
      )}
    </div>
  );
};

export default IndexOverview;
