import React, { useEffect, useState, useMemo } from 'react';
import { CalendarDays, RefreshCw, ChevronLeft, ChevronRight, Filter } from 'lucide-react';
import { fetchWithCache, API_ENDPOINTS } from '../services/dataCache';
import './EconomicCalendar.css';

const IMPACT_ICONS = {
  high: '🔴',
  medium: '🟡',
  low: '⚪',
};

const COUNTRY_FLAGS = {
  US: '🇺🇸', CN: '🇨🇳', EU: '🇪🇺', GB: '🇬🇧', JP: '🇯🇵',
  DE: '🇩🇪', FR: '🇫🇷', AU: '🇦🇺', CA: '🇨🇦', NZ: '🇳🇿', CH: '🇨🇭',
};

const SkeletonRows = () => (
  <div className="ec-day-group">
    <div className="ec-day-header skeleton-line" style={{ width: '120px', height: '20px' }} />
    {[1, 2, 3, 4].map(i => (
      <div key={i} className="ec-event skeleton-event">
        <div className="skeleton-line" style={{ width: '50px' }} />
        <div className="skeleton-line" style={{ width: '30px' }} />
        <div className="skeleton-line wide" />
        <div className="skeleton-line" style={{ width: '60px' }} />
        <div className="skeleton-line" style={{ width: '60px' }} />
        <div className="skeleton-line" style={{ width: '60px' }} />
      </div>
    ))}
  </div>
);

const EconomicCalendar = () => {
  const [events, setEvents] = useState([]);
  const [weekOffset, setWeekOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState('');
  const [note, setNote] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  // Filters
  const [showFilters, setShowFilters] = useState(false);
  const [countryFilter, setCountryFilter] = useState('all');
  const [impactFilter, setImpactFilter] = useState('all');

  const fetchData = async (offset, forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const url = `${API_ENDPOINTS.ECONOMIC_CALENDAR}?week=${offset}`;
      let json;
      if (forceRefresh) {
        const res = await fetch(url);
        if (!res.ok) throw new Error('无法获取财经日历数据');
        json = await res.json();
      } else {
        json = await fetchWithCache(url);
      }
      setEvents(json.data || []);
      setLastUpdated(json.last_updated || '');
      setNote(json.note || '');
      setFromDate(json.from_date || '');
      setToDate(json.to_date || '');
    } catch (e) {
      setError(e.message);
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(weekOffset);
  }, [weekOffset]);

  // Get unique countries from data
  const countries = useMemo(() => {
    const set = new Set(events.map(e => e.country).filter(Boolean));
    return Array.from(set).sort();
  }, [events]);

  // Filter events
  const filteredEvents = useMemo(() => {
    return events.filter(e => {
      if (countryFilter !== 'all' && e.country !== countryFilter) return false;
      if (impactFilter !== 'all' && e.impact !== impactFilter) return false;
      return true;
    });
  }, [events, countryFilter, impactFilter]);

  // Group by date
  const groupedByDate = useMemo(() => {
    const groups = {};
    filteredEvents.forEach(ev => {
      const d = ev.date || 'unknown';
      if (!groups[d]) groups[d] = [];
      groups[d].push(ev);
    });
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
  }, [filteredEvents]);

  const today = new Date().toISOString().slice(0, 10);

  const weekLabel = weekOffset === 0 ? '本周' : weekOffset === 1 ? '下周' : weekOffset === -1 ? '上周' : `${weekOffset > 0 ? '+' : ''}${weekOffset}周`;

  // Determine if actual vs forecast is bullish/bearish
  const getValueClass = (actual, forecast) => {
    if (!actual || !forecast) return '';
    const numActual = parseFloat(actual);
    const numForecast = parseFloat(forecast);
    if (isNaN(numActual) || isNaN(numForecast)) return '';
    if (numActual > numForecast) return 'ec-val-positive';
    if (numActual < numForecast) return 'ec-val-negative';
    return '';
  };

  return (
    <div className="ec-page">
      <div className="ec-header">
        <div className="ec-title">
          <CalendarDays size={22} />
          财经日历
        </div>
        <div className="ec-actions">
          <div className="ec-week-nav">
            <button className="ec-nav-btn" onClick={() => setWeekOffset(w => w - 1)} title="上一周">
              <ChevronLeft size={16} />
            </button>
            <span className="ec-week-label">{weekLabel}</span>
            <button className="ec-nav-btn" onClick={() => setWeekOffset(w => w + 1)} title="下一周">
              <ChevronRight size={16} />
            </button>
            {weekOffset !== 0 && (
              <button className="ec-nav-btn ec-today-btn" onClick={() => setWeekOffset(0)}>
                本周
              </button>
            )}
          </div>
          <button
            className={`ec-filter-btn ${showFilters ? 'active' : ''}`}
            onClick={() => setShowFilters(f => !f)}
            title="筛选"
          >
            <Filter size={16} />
          </button>
          <button onClick={() => fetchData(weekOffset, true)} className="ec-refresh" disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            刷新
          </button>
        </div>
      </div>

      {/* Date range indicator */}
      {fromDate && toDate && (
        <div className="ec-date-range">{fromDate} ~ {toDate}</div>
      )}

      {/* Filters */}
      {showFilters && (
        <div className="ec-filters">
          <div className="ec-filter-group">
            <label>国家/地区</label>
            <select value={countryFilter} onChange={e => setCountryFilter(e.target.value)}>
              <option value="all">全部</option>
              {countries.map(c => (
                <option key={c} value={c}>{COUNTRY_FLAGS[c] || ''} {c}</option>
              ))}
            </select>
          </div>
          <div className="ec-filter-group">
            <label>影响等级</label>
            <select value={impactFilter} onChange={e => setImpactFilter(e.target.value)}>
              <option value="all">全部</option>
              <option value="high">🔴 高影响</option>
              <option value="medium">🟡 中等</option>
              <option value="low">⚪ 低影响</option>
            </select>
          </div>
          {(countryFilter !== 'all' || impactFilter !== 'all') && (
            <button className="ec-filter-clear" onClick={() => { setCountryFilter('all'); setImpactFilter('all'); }}>
              清除筛选
            </button>
          )}
        </div>
      )}

      {error && <div className="ec-error">{error}</div>}
      {note && !loading && <div className="ec-note">{note}</div>}

      <div className="ec-timeline">
        {loading && events.length === 0 ? (
          <SkeletonRows />
        ) : groupedByDate.length > 0 ? (
          groupedByDate.map(([date, dayEvents]) => {
            const isToday = date === today;
            const dateObj = new Date(date + 'T00:00:00');
            const weekday = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][dateObj.getDay()];

            return (
              <div key={date} className={`ec-day-group ${isToday ? 'ec-today' : ''}`}>
                <div className="ec-day-header">
                  <span className="ec-day-date">{date}</span>
                  <span className="ec-day-weekday">{weekday}</span>
                  {isToday && <span className="ec-today-badge">今天</span>}
                  <span className="ec-day-count">{dayEvents.length} 项</span>
                </div>
                <div className="ec-events">
                  {dayEvents.map((ev, idx) => (
                    <div key={idx} className={`ec-event ec-impact-${ev.impact}`}>
                      <div className="ec-event-time">
                        {ev.time || '--:--'}
                      </div>
                      <div className="ec-event-impact" title={ev.impact}>
                        {IMPACT_ICONS[ev.impact] || '⚪'}
                      </div>
                      <div className="ec-event-country">
                        {COUNTRY_FLAGS[ev.country] || ev.country}
                      </div>
                      <div className="ec-event-name">{ev.event}</div>
                      <div className="ec-event-values">
                        <div className="ec-val-group">
                          <span className="ec-val-label">实际</span>
                          <span className={`ec-val ${getValueClass(ev.actual, ev.forecast)}`}>
                            {ev.actual ?? '—'}
                          </span>
                        </div>
                        <div className="ec-val-group">
                          <span className="ec-val-label">预期</span>
                          <span className="ec-val">{ev.forecast ?? '—'}</span>
                        </div>
                        <div className="ec-val-group">
                          <span className="ec-val-label">前值</span>
                          <span className="ec-val">{ev.previous ?? '—'}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })
        ) : (
          <div className="ec-empty">
            {note ? note : '暂无财经日历数据'}
          </div>
        )}
      </div>

      {lastUpdated && (
        <div className="ec-footer">
          更新时间: {lastUpdated}
        </div>
      )}
    </div>
  );
};

export default EconomicCalendar;
