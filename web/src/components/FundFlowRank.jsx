import React, { useEffect, useState } from 'react';
import { Waves, RefreshCw } from 'lucide-react';
import './FundFlowRank.css';

const FundFlowRank = () => {
  const [data, setData] = useState([]);
  const [date, setDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/fund/flow');
      if (!res.ok) throw new Error('无法获取资金流向数据');
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
    <div className="fund-page">
      <div className="fund-header">
        <div className="fund-title">
          <Waves size={22} className="text-blue-600" />
          资金流向榜
        </div>
        <div className="fund-actions">
          <span className="fund-date">{date ? `数据日期: ${date}` : ''}</span>
          <button onClick={fetchData} className="fund-refresh" disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            刷新
          </button>
        </div>
      </div>

      {error ? <div className="fund-error">{error}</div> : null}

      {data.length > 0 ? (
        <div className="fund-table">
          <div className="fund-row fund-header-row">
            <div>代码</div>
            <div>名称</div>
            <div>最新价</div>
            <div>涨跌幅</div>
            <div>主力净流入</div>
            <div>净占比</div>
          </div>
          {data.map(item => (
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
          ))}
        </div>
      ) : (
        <div className="fund-empty">暂无资金流向数据</div>
      )}
    </div>
  );
};

export default FundFlowRank;
