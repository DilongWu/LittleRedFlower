import React, { useState, useEffect } from 'react';
import { Radar, RefreshCw, BarChart2, Layers } from 'lucide-react';
import SectorHeatmap from './SectorHeatmap';
import LimitUpLadder from './LimitUpLadder';
import { fetchWithCache, API_ENDPOINTS } from '../services/dataCache';
import './MarketRadar.css';

// Skeleton loading component
const SkeletonCard = () => (
  <div className="radar-card skeleton-card">
    <div className="skeleton-title"></div>
    <div className="skeleton-content">
      <div className="skeleton-row"></div>
      <div className="skeleton-row"></div>
      <div className="skeleton-row"></div>
      <div className="skeleton-row short"></div>
    </div>
  </div>
);

const MarketRadar = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = async (forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      // Use cache for normal loads, bypass for refresh
      if (forceRefresh) {
        const res = await fetch(API_ENDPOINTS.MARKET_RADAR);
        if (res.ok) {
          const json = await res.json();
          setData(json);
        } else {
          setError("无法获取市场雷达数据");
        }
      } else {
        const json = await fetchWithCache(API_ENDPOINTS.MARKET_RADAR);
        setData(json);
      }
    } catch(e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Show skeleton while loading (but only if no data yet)
  if (loading && !data) {
    return (
      <div className="radar-page">
        <div className="radar-header">
          <div className="radar-title">
            <Radar className="text-red-600" size={28} />
            <span>A股全景雷达 (Market Radar)</span>
          </div>
        </div>
        <div className="radar-grid">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  if (error) return <div className="text-red-500 p-10">{error}</div>;
  if (!data) return null;

  return (
    <div className="radar-page">
       <div className="radar-header">
           <div className="radar-title">
             <Radar className="text-red-600" size={28} />
             <span>A股全景雷达 (Market Radar)</span>
             <span className="text-sm text-gray-400 font-normal ml-auto">数据日期: {data.date}</span>
             <button
               onClick={() => fetchData(true)}
               className="p-2 hover:bg-gray-100 rounded-full"
               disabled={loading}
             >
                <RefreshCw size={16} className={`text-gray-500 ${loading ? 'animate-spin' : ''}`} />
             </button>
           </div>
       </div>

       <div className="radar-grid">
           {/* Left: Heatmap */}
           <div className="radar-card">
               <div className="radar-card-title">
                   <BarChart2 size={20} className="text-blue-600" />
                   板块强弱 (Sector Heatmap)
               </div>
               <SectorHeatmap sectors={data.sectors} />
           </div>

           {/* Right: Ladder */}
           <div className="radar-card">
               <div className="radar-card-title">
                   <Layers size={20} className="text-red-600" />
                   涨停接力天梯 (Limit-Up Ladder)
               </div>
               <div className="overflow-y-auto max-h-[800px] pr-2">
                 <LimitUpLadder ladder={data.ladder} />
               </div>
           </div>
       </div>
    </div>
  );
};

export default MarketRadar;
