import React, { useState, useEffect } from 'react';
import { Radar, RefreshCw, BarChart2, Layers } from 'lucide-react';
import SectorHeatmap from './SectorHeatmap';
import LimitUpLadder from './LimitUpLadder';
import './MarketRadar.css';

const MarketRadar = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
        const res = await fetch('/api/market/radar');
        if (res.ok) {
            const json = await res.json();
            setData(json);
        } else {
            setError("无法获取市场雷达数据");
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

  if (loading && !data) return (
      <div className="p-10 text-center text-gray-500 flex flex-col items-center">
          <RefreshCw className="animate-spin mb-2" />
          <span>正在扫描全市场数据 (AkShare)...</span>
      </div>
  );

  if (error) return <div className="text-red-500 p-10">{error}</div>;
  if (!data) return null;

  return (
    <div className="radar-page">
       <div className="radar-header">
           <div className="radar-title">
             <Radar className="text-red-600" size={28} />
             <span>A股全景雷达 (Market Radar)</span>
             <span className="text-sm text-gray-400 font-normal ml-auto">数据日期: {data.date}</span>
             <button onClick={fetchData} className="p-2 hover:bg-gray-100 rounded-full">
                <RefreshCw size={16} className="text-gray-500" />
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
