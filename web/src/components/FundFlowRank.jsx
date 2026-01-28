import React, { useEffect, useState } from 'react';
import { Waves, RefreshCw } from 'lucide-react';
import { fetchWithCache, API_ENDPOINTS } from '../services/dataCache';
import './FundFlowRank.css';

// Skeleton loading rows
const SkeletonRows = () => (
  <>
    {[1, 2, 3, 4, 5].map(i => (
      <div key={i} className="fund-row skeleton-fund-row">
        <div className="skeleton-cell"></div>
        <div className="skeleton-cell wide"></div>
        <div className="skeleton-cell"></div>
        <div className="skeleton-cell"></div>
        <div className="skeleton-cell wide"></div>
        <div className="skeleton-cell"></div>
      </div>
    ))}
  </>
);

const FundFlowRank = () => {
  const [data, setData] = useState([]);
  const [date, setDate] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      if (forceRefresh) {
        const res = await fetch(API_ENDPOINTS.FUND_FLOW);
        if (!res.ok) throw new Error('无法获取资金流向数据');
        const json = await res.json();
        setData(json.data || []);
        setDate(json.date || '');
      } else {
        const json = await fetchWithCache(API_ENDPOINTS.FUND_FLOW);
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
    <div className="fund-page">
      <div className="fund-header">
        <div className="fund-title">
          <Waves size={22} className="text-blue-600" />
          资金流向榜
        </div>
        <div className="fund-actions">
          <span className="fund-date">{date ? `数据日期: ${date}` : ''}</span>
          <button onClick={() => fetchData(true)} className="fund-refresh" disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            刷新
          </button>
        </div>
      </div>

      {error ? <div className="fund-error">{error}</div> : null}

      <div className="fund-table">
        <div className="fund-row fund-header-row">
          <div>代码</div>
          <div>名称</div>
          <div>最新价</div>
          <div>涨跌幅</div>
          <div>主力净流入</div>
          <div>净占比</div>
        </div>
        {loading && data.length === 0 ? (
          <SkeletonRows />
        ) : data.length > 0 ? (
          data.map(item => (
            <div key={`${item.code}-${item.name}`} className="fund-row">
              <div>{item.code}</div>
              <div>{item.name}</div>
              <div>{item.price ?? '-'}</div>
              <div className={String(item.change_pct || '').startsWith('-') ? 'down' : 'up'}>
                {item.change_pct ?? '-'}
              </div>
              <div className="up">{item.net_inflow ?? '-'}</div>
              <div>{item.net_ratio ?? '-'}</div>
            </div>
          ))
        ) : (
          <div className="fund-empty">暂无资金流向数据</div>
        )}
      </div>
    </div>
  );
};

export default FundFlowRank;
