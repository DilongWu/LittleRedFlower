import React, { useEffect, useState } from 'react';
import { Flame, RefreshCw } from 'lucide-react';
import { fetchWithCache, API_ENDPOINTS } from '../services/dataCache';
import './HotConcepts.css';

// Skeleton loading cards
const SkeletonCards = () => (
  <>
    {[1, 2, 3, 4, 5, 6].map(i => (
      <div key={i} className="concept-card skeleton-concept-card">
        <div className="skeleton-concept-line name"></div>
        <div className="skeleton-concept-line change"></div>
        <div className="skeleton-concept-line lead"></div>
      </div>
    ))}
  </>
);

const HotConcepts = () => {
  const [data, setData] = useState([]);
  const [date, setDate] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      if (forceRefresh) {
        const res = await fetch(API_ENDPOINTS.HOT_CONCEPTS);
        if (!res.ok) throw new Error('无法获取题材数据');
        const json = await res.json();
        setData(json.data || []);
        setDate(json.date || '');
      } else {
        const json = await fetchWithCache(API_ENDPOINTS.HOT_CONCEPTS);
        setData(json.data || []);
        setDate(json.date || '');
      }
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
          <button onClick={() => fetchData(true)} className="concept-refresh" disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            刷新
          </button>
        </div>
      </div>

      {error ? <div className="concept-error">{error}</div> : null}

      <div className="concept-grid">
        {loading && data.length === 0 ? (
          <SkeletonCards />
        ) : data.length > 0 ? (
          data.map(item => (
            <div key={item.name} className="concept-card">
              <div className="concept-name">{item.name}</div>
              <div className={item.change >= 0 ? 'concept-change up' : 'concept-change down'}>
                {item.change >= 0 ? '+' : ''}{Number(item.change).toFixed(2)}%
              </div>
              <div className="concept-lead">领涨: {item.lead || '-'}</div>
            </div>
          ))
        ) : (
          <div className="concept-empty">暂无题材数据</div>
        )}
      </div>
    </div>
  );
};

export default HotConcepts;
