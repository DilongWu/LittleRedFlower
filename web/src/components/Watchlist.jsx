import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Star, RefreshCw, Plus, Pin, Trash2, Clock, Search } from 'lucide-react';
import { fetchWithCache } from '../services/dataCache';
import './Watchlist.css';

// ── Constants ───────────────────────────────────────────────────
const LS_KEY = 'watchlist_stocks';
const DEFAULT_WATCHLIST = ['MSFT', 'AAPL', 'GOOGL', '600519'];

function loadWatchlist() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch { /* ignore */ }
  return [...DEFAULT_WATCHLIST];
}

function saveWatchlist(list) {
  localStorage.setItem(LS_KEY, JSON.stringify(list));
}

// ── Glowing MiniTrendLine ───────────────────────────────────────
const GlowTrendLine = ({ trend, changePercent }) => {
  if (!trend || trend.length < 2) return null;
  const valid = trend.filter(v => v != null && !isNaN(v));
  if (valid.length < 2) return null;

  const w = 200, h = 48;
  const max = Math.max(...valid), min = Math.min(...valid);
  const range = max - min || 1;

  const points = valid
    .map((v, i) => {
      const x = (i / (valid.length - 1)) * w;
      const y = h - ((v - min) / range) * (h - 4) - 2;
      return `${x},${y}`;
    })
    .join(' ');

  const isUp = changePercent >= 0;
  const stroke = isUp ? '#ef4444' : '#16a34a';
  const glowColor = isUp ? 'rgba(239,68,68,0.45)' : 'rgba(22,163,106,0.45)';
  const gradId = isUp ? 'glowUp' : 'glowDown';

  return (
    <svg width={w} height={h} style={{ '--trend-glow': glowColor }}>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.25" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      {/* area fill */}
      <polygon
        points={`0,${h} ${points} ${w},${h}`}
        fill={`url(#${gradId})`}
      />
      {/* line */}
      <polyline
        fill="none"
        stroke={stroke}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
    </svg>
  );
};

// ── Skeleton Card ───────────────────────────────────────────────
const SkeletonCard = () => (
  <div className="wl-card wl-skeleton">
    <div className="wl-skel-line title" />
    <div className="wl-skel-line price" />
    <div className="wl-skel-line trend" />
    <div className="wl-skel-line meta" />
  </div>
);

// ── Stock Card ──────────────────────────────────────────────────
const StockCard = ({ stock, onRemove, onPin, isPinned }) => {
  const [flash, setFlash] = useState(false);
  const prevPrice = useRef(stock.price);

  useEffect(() => {
    if (prevPrice.current !== stock.price) {
      setFlash(true);
      const t = setTimeout(() => setFlash(false), 600);
      prevPrice.current = stock.price;
      return () => clearTimeout(t);
    }
  }, [stock.price]);

  if (stock.error) {
    return (
      <div className="wl-card error">
        <div className="wl-card-header">
          <span className="wl-card-emoji">❌</span>
          <div className="wl-card-title">
            <div className="wl-card-name">{stock.symbol}</div>
          </div>
          <div className="wl-card-actions" style={{ opacity: 1 }}>
            <button className="wl-card-action-btn delete" onClick={() => onRemove(stock.symbol)} title="删除">
              <Trash2 size={14} />
            </button>
          </div>
        </div>
        <div className="wl-error-msg">数据获取失败</div>
      </div>
    );
  }

  const isUp = stock.change_percent >= 0;
  const isAShare = stock.market === 'A';
  const currencySymbol = isAShare ? '¥' : '$';

  return (
    <div className={`wl-card ${isUp ? 'up' : 'down'}`}>
      {/* Header */}
      <div className="wl-card-header">
        <span className="wl-card-emoji">{stock.emoji || '📊'}</span>
        <div className="wl-card-title">
          <div className="wl-card-name">{stock.name}</div>
          <div className="wl-card-symbol">{stock.symbol}</div>
        </div>
        <span className={`wl-card-market-badge ${isAShare ? 'a-share' : 'us-share'}`}>
          {isAShare ? 'A股' : 'US'}
        </span>
        <div className="wl-card-actions">
          <button
            className={`wl-card-action-btn ${isPinned ? 'pinned' : ''}`}
            onClick={() => onPin(stock.symbol)}
            title={isPinned ? '取消置顶' : '置顶'}
          >
            <Pin size={14} />
          </button>
          <button className="wl-card-action-btn delete" onClick={() => onRemove(stock.symbol)} title="删除">
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Price */}
      <div className="wl-price-row">
        <div className={`wl-price ${flash ? 'flash' : ''}`}>
          {currencySymbol}{stock.price}
        </div>
        <div className={`wl-change ${isUp ? 'up' : 'down'}`}>
          {isUp ? '+' : ''}{stock.change} ({isUp ? '+' : ''}{stock.change_percent}%)
        </div>
      </div>

      {/* Trend */}
      <div className="wl-trend">
        <GlowTrendLine trend={stock.trend} changePercent={stock.change_percent} />
      </div>

      {/* Meta */}
      <div className="wl-meta">
        <div className="wl-meta-item">
          <span className="wl-meta-label">成交量</span>
          <span className="wl-meta-value">{stock.volume_str || 'N/A'}</span>
        </div>
        <div className="wl-meta-item">
          <span className="wl-meta-label">{isAShare ? '成交额' : '市值'}</span>
          <span className="wl-meta-value">{isAShare ? (stock.turnover_str || 'N/A') : (stock.market_cap_str || 'N/A')}</span>
        </div>
      </div>

      {/* OHLC */}
      <div className="wl-ohlc">
        开: {currencySymbol}{stock.open} | 高: {currencySymbol}{stock.high} | 低: {currencySymbol}{stock.low}
      </div>
    </div>
  );
};

// ── Main Component ──────────────────────────────────────────────
const Watchlist = () => {
  const [symbols, setSymbols] = useState(loadWatchlist);
  const [pinnedSet, setPinnedSet] = useState(() => {
    try {
      const raw = localStorage.getItem('watchlist_pinned');
      return raw ? new Set(JSON.parse(raw)) : new Set();
    } catch { return new Set(); }
  });
  const [quotes, setQuotes] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [addInput, setAddInput] = useState('');
  const [updatedAt, setUpdatedAt] = useState(null);

  // persist symbols
  useEffect(() => { saveWatchlist(symbols); }, [symbols]);

  // persist pinned
  useEffect(() => {
    localStorage.setItem('watchlist_pinned', JSON.stringify([...pinnedSet]));
  }, [pinnedSet]);

  // fetch data
  const fetchData = useCallback(async (force = false) => {
    if (symbols.length === 0) { setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      const url = `/api/watchlist/quotes?symbols=${symbols.join(',')}`;
      let json;
      if (force) {
        const res = await fetch(url);
        if (!res.ok) throw new Error('获取自选股数据失败');
        json = await res.json();
      } else {
        json = await fetchWithCache(url);
      }
      setQuotes(json.quotes || {});
      setUpdatedAt(json.updated_at);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [symbols]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // auto-refresh every 60s
  useEffect(() => {
    const iv = setInterval(() => fetchData(true), 60000);
    return () => clearInterval(iv);
  }, [fetchData]);

  // handlers
  const handleAdd = () => {
    const sym = addInput.trim().toUpperCase();
    if (!sym) return;
    if (symbols.includes(sym)) { setAddInput(''); return; }
    setSymbols(prev => [...prev, sym]);
    setAddInput('');
  };

  const handleRemove = (sym) => {
    setSymbols(prev => prev.filter(s => s !== sym));
    setPinnedSet(prev => { const n = new Set(prev); n.delete(sym); return n; });
    setQuotes(prev => { const n = { ...prev }; delete n[sym]; return n; });
  };

  const handlePin = (sym) => {
    setPinnedSet(prev => {
      const n = new Set(prev);
      if (n.has(sym)) n.delete(sym); else n.add(sym);
      return n;
    });
  };

  // sorted: pinned first, then original order
  const sortedSymbols = [...symbols].sort((a, b) => {
    const ap = pinnedSet.has(a) ? 0 : 1;
    const bp = pinnedSet.has(b) ? 0 : 1;
    if (ap !== bp) return ap - bp;
    return symbols.indexOf(a) - symbols.indexOf(b);
  });

  // build cards data (merge error placeholders for missing)
  const cardsData = sortedSymbols.map(sym => {
    if (quotes[sym]) return quotes[sym];
    return { symbol: sym, error: true };
  });

  return (
    <div className="watchlist-dark-bg">
      <div className="watchlist-page">
        {/* Header */}
        <div className="watchlist-header">
          <div className="watchlist-header-left">
            <Star size={24} className="watchlist-header-icon" />
            <h2>自选股看板</h2>
          </div>
          <div className="watchlist-actions">
            <button className="wl-btn" onClick={() => fetchData(true)} disabled={loading} title="刷新数据">
              <RefreshCw size={15} className={loading ? 'spin' : ''} />
              刷新
            </button>
          </div>
        </div>

        {/* Add bar */}
        <div className="watchlist-add-bar">
          <input
            className="watchlist-search-input"
            type="text"
            placeholder="输入股票代码 (如 TSLA 或 000001)"
            value={addInput}
            onChange={e => setAddInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleAdd(); }}
          />
          <button className="wl-add-btn" onClick={handleAdd}>
            <Plus size={15} /> 添加
          </button>
        </div>

        {/* Update time */}
        {updatedAt && (
          <div className="watchlist-update-time">
            <Clock size={13} />
            更新: {new Date(updatedAt).toLocaleString('zh-CN')}
          </div>
        )}

        {/* Error */}
        {error && <div className="watchlist-error">⚠️ {error}</div>}

        {/* Grid */}
        {loading && Object.keys(quotes).length === 0 ? (
          <div className="watchlist-grid">
            {symbols.map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : cardsData.length > 0 ? (
          <div className="watchlist-grid">
            {cardsData.map(stock => (
              <StockCard
                key={stock.symbol}
                stock={stock}
                onRemove={handleRemove}
                onPin={handlePin}
                isPinned={pinnedSet.has(stock.symbol)}
              />
            ))}
          </div>
        ) : (
          <div className="watchlist-empty">
            <p>暂无自选股</p>
            <p style={{ fontSize: '0.9rem' }}>在上方输入框添加股票代码开始</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Watchlist;
