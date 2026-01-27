import React, { useState } from 'react';
import { Search, TrendingUp, Activity, AlertTriangle } from 'lucide-react';
import './StockDiagnosis.css';

const StockDiagnosis = () => {
  const [symbol, setSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const handleQuery = async () => {
    if (!symbol.trim()) {
      setError('请输入股票代码，例如 000001');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch('/api/stock/diagnosis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: symbol.trim(), days: 60 })
      });

      if (!res.ok) {
        const msg = await res.json();
        throw new Error(msg.detail || '诊断失败');
      }

      const json = await res.json();
      setData(json);
    } catch (e) {
      setError(e.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="diagnosis-page">
      <div className="diagnosis-header">
        <div className="diagnosis-title">
          <Activity size={22} className="text-red-600" />
          个股诊断
        </div>
        <div className="diagnosis-search">
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="输入股票代码，例如 000001"
            className="diagnosis-input"
          />
          <button onClick={handleQuery} disabled={loading} className="diagnosis-button">
            <Search size={16} />
            {loading ? '诊断中...' : '开始诊断'}
          </button>
        </div>
      </div>

      {error ? (
        <div className="diagnosis-error">
          <AlertTriangle size={16} />
          {error}
        </div>
      ) : null}

      {data ? (
        <div className="diagnosis-grid">
          <div className="diagnosis-card">
            <div className="card-title">
              <TrendingUp size={16} /> 价格与趋势
            </div>
            <div className="kv">
              <div>最新价</div>
              <div className="kv-value">{data.price}</div>
            </div>
            <div className="kv">
              <div>涨跌幅</div>
              <div className={data.change_pct >= 0 ? 'kv-value up' : 'kv-value down'}>
                {data.change_pct >= 0 ? '+' : ''}{data.change_pct}%
              </div>
            </div>
            <div className="kv">
              <div>趋势判断</div>
              <div className="kv-value">{data.trend}</div>
            </div>
          </div>

          <div className="diagnosis-card">
            <div className="card-title">均线结构</div>
            <div className="kv">
              <div>MA5</div>
              <div className="kv-value">{data.ma5 ?? '-'}</div>
            </div>
            <div className="kv">
              <div>MA10</div>
              <div className="kv-value">{data.ma10 ?? '-'}</div>
            </div>
            <div className="kv">
              <div>MA20</div>
              <div className="kv-value">{data.ma20 ?? '-'}</div>
            </div>
          </div>

          <div className="diagnosis-card">
            <div className="card-title">量能表现</div>
            <div className="kv">
              <div>近5日 / 20日量比</div>
              <div className="kv-value">{data.vol_ratio ?? '-'}</div>
            </div>
            <div className="kv">
              <div>数据日期</div>
              <div className="kv-value">{data.date}</div>
            </div>
          </div>

          <div className="diagnosis-card">
            <div className="card-title">基础信息</div>
            <div className="kv">
              <div>股票简称</div>
              <div className="kv-value">{data.basic?.['股票简称'] || '-'}</div>
            </div>
            <div className="kv">
              <div>所属行业</div>
              <div className="kv-value">{data.basic?.['行业'] || '-'}</div>
            </div>
            <div className="kv">
              <div>上市时间</div>
              <div className="kv-value">{data.basic?.['上市时间'] || '-'}</div>
            </div>
          </div>
        </div>
      ) : (
        <div className="diagnosis-empty">请输入代码开始诊断。</div>
      )}
    </div>
  );
};

export default StockDiagnosis;
