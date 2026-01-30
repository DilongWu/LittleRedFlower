import React, { useEffect, useState } from 'react';
import { TrendingUp, RefreshCw, DollarSign, Clock } from 'lucide-react';
import { fetchWithCache, API_ENDPOINTS } from '../services/dataCache';
import './USTechStocks.css';

// 简化的迷你趋势图组件
const MiniTrendLine = ({ trend, changePercent }) => {
  if (!trend || trend.length === 0) return null;

  const validTrend = trend.filter(v => v != null && !isNaN(v));
  if (validTrend.length === 0) return null;

  const max = Math.max(...validTrend);
  const min = Math.min(...validTrend);
  const range = max - min || 1;
  const width = 180;
  const height = 50;

  const points = validTrend
    .map((v, i) => {
      const x = (i / (validTrend.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg width={width} height={height} className="mini-trend">
      <polyline
        fill="none"
        stroke={changePercent >= 0 ? '#ef4444' : '#16a34a'}
        strokeWidth="2"
        points={points}
      />
    </svg>
  );
};

// 骨架屏加载卡片
const SkeletonCard = () => (
  <div className="us-tech-card skeleton-card">
    <div className="skeleton-line title"></div>
    <div className="skeleton-line price"></div>
    <div className="skeleton-line trend"></div>
    <div className="skeleton-line meta"></div>
  </div>
);

// 单个股票卡片
const StockCard = ({ stock }) => {
  if (stock.error) {
    return (
      <div className="us-tech-card error-card">
        <div className="stock-header">
          <span className="stock-emoji">{stock.emoji || '❌'}</span>
          <div className="stock-title">
            <div className="stock-name">{stock.name}</div>
            <div className="stock-symbol">{stock.symbol}</div>
          </div>
        </div>
        <div className="error-message">数据获取失败</div>
      </div>
    );
  }

  const isUp = stock.change_percent >= 0;
  const isStale = stock.is_stale || stock.from_cache;

  return (
    <div className={`us-tech-card ${isUp ? 'up-card' : 'down-card'}`}>
      {/* 头部 */}
      <div className="stock-header">
        <span className="stock-emoji">{stock.emoji || '📊'}</span>
        <div className="stock-title">
          <div className="stock-name">{stock.name}</div>
          <div className="stock-symbol">{stock.symbol}</div>
        </div>
        {isStale && <span className="cache-badge" title="使用缓存数据">📦</span>}
      </div>

      {/* 价格和涨跌幅 */}
      <div className="stock-price-row">
        <div className="stock-price">${stock.price}</div>
        <div className={`stock-change ${isUp ? 'up' : 'down'}`}>
          {isUp ? '+' : ''}{stock.change} ({isUp ? '+' : ''}{stock.change_percent}%)
        </div>
      </div>

      {/* 趋势图 */}
      <div className="stock-trend">
        <MiniTrendLine trend={stock.trend} changePercent={stock.change_percent} />
      </div>

      {/* 底部元数据 */}
      <div className="stock-meta">
        <div className="meta-item">
          <span className="meta-label">成交量:</span>
          <span className="meta-value">{stock.volume_str || 'N/A'}</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">市值:</span>
          <span className="meta-value">{stock.market_cap_str || 'N/A'}</span>
        </div>
      </div>

      {/* 开高低 */}
      <div className="stock-ohlc">
        开: ${stock.open} | 高: ${stock.high} | 低: ${stock.low}
      </div>
    </div>
  );
};

// 主组件
const USTechStocks = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generating, setGenerating] = useState(false);

  const fetchData = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      if (forceRefresh) {
        const res = await fetch('/api/us-tech/latest');
        if (!res.ok) throw new Error('无法获取美股数据');
        const json = await res.json();
        setData(json);
      } else {
        const json = await fetchWithCache('/api/us-tech/latest');
        setData(json);
      }
    } catch (e) {
      setError(e.message);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const triggerGenerate = async () => {
    setGenerating(true);
    try {
      const res = await fetch('/api/trigger/us-tech', { method: 'POST' });
      if (!res.ok) throw new Error('触发生成失败');

      // 等待3秒后自动刷新
      setTimeout(() => {
        fetchData(true);
        setGenerating(false);
      }, 3000);
    } catch (e) {
      alert(`生成失败: ${e.message}`);
      setGenerating(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const summary = data?.summary;
  const stocks = data?.stocks || [];
  const stocksArray = Object.values(stocks);

  return (
    <div className="us-tech-page">
      {/* 页面头部 */}
      <div className="us-tech-header">
        <div className="header-left">
          <DollarSign size={24} className="header-icon" />
          <h2>美股科技巨头动态</h2>
        </div>
        <div className="header-actions">
          <button
            onClick={() => fetchData(true)}
            className="action-btn refresh-btn"
            disabled={loading}
            title="刷新数据"
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            刷新
          </button>
          <button
            onClick={triggerGenerate}
            className="action-btn generate-btn"
            disabled={generating}
            title="手动生成最新数据"
          >
            <TrendingUp size={16} />
            {generating ? '生成中...' : '生成数据'}
          </button>
        </div>
      </div>

      {/* 摘要信息 */}
      {summary && (
        <div className="us-tech-summary">
          <div className="summary-item">
            <span className="summary-label">总计:</span>
            <span className="summary-value">{summary.total} 只</span>
          </div>
          <div className="summary-item success">
            <span className="summary-label">上涨:</span>
            <span className="summary-value">↑ {summary.up}</span>
          </div>
          <div className="summary-item danger">
            <span className="summary-label">下跌:</span>
            <span className="summary-value">↓ {summary.down}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">平均涨幅:</span>
            <span className={`summary-value ${summary.avg_change >= 0 ? 'success' : 'danger'}`}>
              {summary.avg_change >= 0 ? '+' : ''}{summary.avg_change}%
            </span>
          </div>
          {summary.top_gainer && (
            <div className="summary-item">
              <span className="summary-label">领涨:</span>
              <span className="summary-value success">
                {summary.top_gainer.name} (+{summary.top_gainer.change_percent}%)
              </span>
            </div>
          )}
          {summary.top_loser && (
            <div className="summary-item">
              <span className="summary-label">领跌:</span>
              <span className="summary-value danger">
                {summary.top_loser.name} ({summary.top_loser.change_percent}%)
              </span>
            </div>
          )}
        </div>
      )}

      {/* 更新时间 */}
      {data?.updated_at && (
        <div className="update-time">
          <Clock size={14} />
          更新时间: {new Date(data.updated_at).toLocaleString('zh-CN')}
          {data.elapsed_time && ` (耗时 ${data.elapsed_time}秒)`}
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="us-tech-error">
          ⚠️ {error}
        </div>
      )}

      {/* 股票卡片网格 */}
      {loading && stocksArray.length === 0 ? (
        <div className="us-tech-grid">
          {[...Array(9)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : stocksArray.length > 0 ? (
        <div className="us-tech-grid">
          {stocksArray.map(stock => (
            <StockCard key={stock.symbol} stock={stock} />
          ))}
        </div>
      ) : (
        <div className="us-tech-empty">
          <p>暂无美股数据</p>
          <button onClick={triggerGenerate} className="action-btn generate-btn">
            点击生成数据
          </button>
        </div>
      )}
    </div>
  );
};

export default USTechStocks;
