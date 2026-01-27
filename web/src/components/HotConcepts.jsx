import React, { useEffect, useState } from 'react';
import { Flame, RefreshCw } from 'lucide-react';
import './HotConcepts.css';

const HotConcepts = () => {
  const [data, setData] = useState([]);
  const [date, setDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/concept/hot');
      if (!res.ok) throw new Error('无法获取题材数据');
      const json = await res.json();
      setData(json.data || []);
      setDate(json.date || '');
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
    <div className="concept-page">
      <div className="concept-header">
        <div className="concept-title">
          <Flame size={22} className="text-orange-500" />
          热点题材跟踪
        </div>
        <div className="concept-actions">
          <span className="concept-date">{date ? `数据日期: ${date}` : ''}</span>
          <button onClick={fetchData} className="concept-refresh" disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            刷新
          </button>
        </div>
      </div>

      {error ? <div className="concept-error">{error}</div> : null}

      {data.length > 0 ? (
        <div className="concept-grid">
          {data.map(item => (
            <div key={item.name} className="concept-card">
              <div className="concept-name">{item.name}</div>
              <div className={item.change >= 0 ? 'concept-change up' : 'concept-change down'}>
                {item.change >= 0 ? '+' : ''}{Number(item.change).toFixed(2)}%
              </div>
              <div className="concept-lead">领涨: {item.lead || '-'}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="concept-empty">暂无题材数据</div>
      )}
    </div>
  );
};

export default HotConcepts;
