import React from 'react';
import { Activity, Clock, Zap } from 'lucide-react';
import './SentimentGauge.css';

const SentimentGauge = ({ data, loading }) => {
  if (loading && !data) return <div className="loading-container">正在分析市场情绪...</div>;
  if (!data) return null;

  const { score, label, summary, is_placeholder } = data;
  
  // Angle mapping: 0 to 100 maps to -90deg to 90deg
  const angle = Math.min(Math.max((score / 100) * 180 - 90, -90), 90);

  // Color logic for Chinese market: 0 (Fear/Green/Blue) -> 100 (Greed/Red)
  let color = '#3b82f6'; 
  if (score <= 20) color = '#22c55e'; // Green (Fear)
  else if (score <= 40) color = '#84cc16'; // Light Green
  else if (score <= 60) color = '#eab308'; // Yellow/Neutral
  else if (score <= 80) color = '#f97316'; // Orange
  else color = '#ef4444'; // Red (Greed)

  // Generate Ticks
  const ticks = [];
  for (let i = 0; i <= 100; i += 2) {
      const isMajor = i % 10 === 0;
      const tickAngle = (i / 100) * 180 - 90;
      const innerRadius = isMajor ? 70 : 75;
      const outerRadius = 80;
      
      // Calculate coordinates
      const rad = (tickAngle * Math.PI) / 180;
      const x1 = 100 + innerRadius * Math.cos(rad);
      const y1 = 100 + innerRadius * Math.sin(rad);
      const x2 = 100 + outerRadius * Math.cos(rad);
      const y2 = 100 + outerRadius * Math.sin(rad);

      ticks.push(
          <line 
            key={i} 
            x1={x1} y1={y1} x2={x2} y2={y2} 
            className={`gauge-tick ${isMajor ? 'major' : ''}`}
            strokeLinecap="round"
          />
      );
  }

  return (
    <div className="sentiment-card">
      {/* Gauge Visual */}
      <div className="gauge-container">
        <svg viewBox="0 0 200 110" className="gauge-svg">
            {/* Gradient Definition */}
            <defs>
                <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#22c55e" stopOpacity="0.8" />
                    <stop offset="50%" stopColor="#eab308" stopOpacity="0.8" />
                    <stop offset="100%" stopColor="#ef4444" stopOpacity="0.8" />
                </linearGradient>
            </defs>
            
            {/* Ticks underneath */}
            {ticks}

            {/* Main Arc */}
            <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="#f3f4f6" strokeWidth="12" strokeLinecap="round" />
            <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="url(#gaugeGradient)" strokeWidth="12" strokeLinecap="round" />

            {/* Needle */}
            <g className="gauge-needle" style={{ transform: `rotate(${angle}deg)` }}>
                {/* Needle Shadow */}
                <line x1="100" y1="100" x2="100" y2="25" stroke="rgba(0,0,0,0.1)" strokeWidth="6" strokeLinecap="round" transform="translate(2, 2)" />
                {/* Needle Main */}
                <line x1="100" y1="100" x2="100" y2="25" stroke="#374151" strokeWidth="4" strokeLinecap="round" />
                <circle cx="100" cy="100" r="6" fill="#1f2937" stroke="white" strokeWidth="2" />
            </g>
            
            {/* Axis Labels */}
            <text x="15" y="120" textAnchor="middle" className="text-[10px] fill-emerald-600 font-bold" style={{fontSize: '10px', fill: '#22c55e'}}>恐慌</text>
            <text x="185" y="120" textAnchor="middle" className="text-[10px] fill-red-600 font-bold" style={{fontSize: '10px', fill: '#ef4444'}}>贪婪</text>
        </svg>
        
        {/* Score Display Overlay */}
        <div className="score-overlay">
            <div className="score-value" style={{ color }}>{score}</div>
            <div className="score-label">{label}</div>
        </div>
      </div>
      
      {/* Text Info */}
      <div className="info-section">
        <h3 className="info-title">
            <Activity size={24} className="info-title-icon"/>
            AI 市场情绪
        </h3>
        <div className="info-desc">
            {is_placeholder ? (
                <span style={{color: '#9ca3af', fontStyle: 'italic'}}>等待市场数据生成中... (Waiting for analysis)</span>
            ) : summary}
        </div>
        <div className="info-footer">
             <div style={{display:'flex', alignItems:'center', gap:'4px'}}>
                <Clock size={14}/>
                <span>{data.timestamp ? new Date(data.timestamp).toLocaleString() : 'N/A'}</span>
             </div>
             <span className="tag-ai">
                <Zap size={12} style={{display:'inline', marginRight:'4px'}}/>
                Azure OpenAI
             </span>
        </div>
      </div>
    </div>
  );
};

export default SentimentGauge;
