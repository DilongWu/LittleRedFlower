import React from 'react';
import { Activity, TrendingUp, AlertTriangle, ShieldCheck, Thermometer, ArrowRight, Zap } from 'lucide-react';
import './SentimentGauge.css'; // Keep base styles
import './SentimentDashboard.css'; // New layout styles

const SentimentDashboard = ({ data, loading }) => {
  if (loading && !data) return (
    <div className="dashboard-container">
       <div className="dash-card" style={{height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <span className="animate-pulse text-gray-400">正在分析全网情绪数据...</span>
       </div>
    </div>
  );
  
  if (!data) return null;

  const { score, label, summary, is_placeholder, history } = data;
  
  // Helpers
  const getColor = (s) => {
    if (s <= 20) return '#22c55e';
    if (s <= 40) return '#84cc16';
    if (s <= 60) return '#eab308';
    if (s <= 80) return '#f97316';
    return '#ef4444';
  };
  
  const currentColor = getColor(score);

  // Derived Advice Logic (Frontend Mock)
  let positionAdvice = "5-6成";
  let strategy = "持股观望";
  let icon = <ShieldCheck size={18} className="text-yellow-600"/>;
  
  if (score <= 20) {
      positionAdvice = "7-8成 (抄底)";
      strategy = "分批建仓，贪婪时刻";
      icon = <Zap size={18} className="text-green-600"/>;
  } else if (score >= 80) {
      positionAdvice = "2-3成 (止盈)";
      strategy = "越涨越卖，且战且退";
      icon = <AlertTriangle size={18} className="text-red-600"/>;
  } else if (score > 60) {
      positionAdvice = "6-7成 (持有)";
      strategy = "去弱留强，跟随趋势";
      icon = <TrendingUp size={18} className="text-orange-600"/>;
  }

  // Draw History Chart
  const renderHistoryChart = () => {
      // Mock history if empty (for preview)
      const chartData = (history && history.length > 0) ? history : [
        {date: 'T-4', score: 50}, {date: 'T-3', score: 55}, {date: 'T-2', score: 48}, {date: 'T-1', score: 52}, {date: 'Today', score: score}
      ];

      const height = 150;
      const width = 600; // viewBox width
      const padding = 30;
      
      if (chartData.length < 2) return <div className="text-gray-400 text-sm text-center py-10">历史数据积累中...</div>;

      const xStep = (width - padding * 2) / (chartData.length - 1);
      
      // Calculate points
      const points = chartData.map((d, i) => {
          const x = padding + i * xStep;
          const y = height - padding - (d.score / 100) * (height - padding * 2);
          return `${x},${y}`;
      }).join(' ');
      
      // Dots
      const dots = chartData.map((d, i) => {
          const x = padding + i * xStep;
          const y = height - padding - (d.score / 100) * (height - padding * 2);
          const dotColor = getColor(d.score);
          return (
              <g key={i} className="group">
                  <circle cx={x} cy={y} r="4" fill="white" stroke={dotColor} strokeWidth="2" className="chart-dot"/>
                  <text x={x} y={height - 5} className="chart-label">{d.date.slice(5)}</text>
                  <text x={x} y={y - 10} className="chart-label" style={{opacity: 0.5, fontSize: '9px'}}>{d.score}</text>
              </g>
          );
      });

      return (
          <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg">
              {/* Grid Lines */}
              <line x1={padding} y1={height/2} x2={width-padding} y2={height/2} className="chart-axis-dash" />
              <line x1={padding} y1={padding} x2={width-padding} y2={padding} className="chart-axis" strokeOpacity="0.1"/>
              <line x1={padding} y1={height-padding} x2={width-padding} y2={height-padding} className="chart-axis"/>
              
              {/* The Line */}
              <polyline points={points} fill="none" stroke="url(#lineGradient)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
              
              <defs>
                <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    {chartData.map((d, i) => (
                        <stop key={i} offset={`${(i/(chartData.length-1))*100}%`} stopColor={getColor(d.score)} />
                    ))}
                </linearGradient>
              </defs>

              {dots}
          </svg>
      );
  };

  // Render Gauge Ticks logic (simplified copy from Gauge component)
  const angle = Math.min(Math.max((score / 100) * 180 - 90, -90), 90);
  const ticks = [];
  for (let i = 0; i <= 100; i += 2) {
      const isMajor = i % 10 === 0;
      const tickAngle = (i / 100) * 180 - 90;
      const innerRadius = isMajor ? 70 : 75;
      const outerRadius = 80;
      const rad = (tickAngle * Math.PI) / 180;
      const x1 = 100 + innerRadius * Math.cos(rad);
      const y1 = 100 + innerRadius * Math.sin(rad);
      const x2 = 100 + outerRadius * Math.cos(rad);
      const y2 = 100 + outerRadius * Math.sin(rad);
      
      // Only render ticks > -10 and < 210 in current viewBox? 
      // Gauge SVG coords: 0 0 200 110. Center 100, 100.
      ticks.push(<line key={i} x1={x1} y1={y1} x2={x2} y2={y2} className={`gauge-tick ${isMajor ? 'major' : ''}`} strokeLinecap="round"/>);
  }

  return (
    <div className="dashboard-container">
      
      {/* Header Area: 2 Columns */}
      <div className="dashboard-grid">
         
         {/* Left: Enhanced Gauge */}
         <div className="dash-card" style={{display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center'}}>
            <div className="dash-title" style={{alignSelf:'flex-start', fontSize:'1rem'}}>
                <AlertTriangle size={18} color={currentColor}/> 
                今日情绪指数
            </div>
            
            <div className="gauge-wrapper">
                <div className="gauge-svg-box">
                    <svg viewBox="0 0 200 120" className="gauge-svg">
                        <defs>
                            <linearGradient id="gGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                <stop offset="0%" stopColor="#22c55e" stopOpacity="1" />
                                <stop offset="50%" stopColor="#eab308" stopOpacity="1" />
                                <stop offset="100%" stopColor="#ef4444" stopOpacity="1" />
                            </linearGradient>
                        </defs>
                        {ticks}
                        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="#f3f4f6" strokeWidth="12" strokeLinecap="round" />
                        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="url(#gGradient)" strokeWidth="12" strokeLinecap="round" opacity="0.9"/>
                        <g className="gauge-needle" style={{ transform: `rotate(${angle}deg)` }}>
                            <line x1="100" y1="100" x2="100" y2="25" stroke="#374151" strokeWidth="4" strokeLinecap="round" />
                            <circle cx="100" cy="100" r="5" fill="#1f2937" />
                        </g>
                        <text x="15" y="120" className="text-[10px] fill-emerald-600 font-bold" style={{fontSize: '10px', fill: '#22c55e'}}>恐慌(0)</text>
                        <text x="185" y="120" className="text-[10px] fill-red-600 font-bold" style={{fontSize: '10px', fill: '#ef4444', textAnchor:'end'}}>贪婪(100)</text>
                    </svg>
                </div>
                
                <div style={{textAlign:'center', marginTop:'-10px'}}>
                    <div style={{fontSize:'3rem', fontWeight:'900', color: currentColor, lineHeight: 1}}>{score}</div>
                    <div style={{color: currentColor, fontWeight:'600', textTransform:'uppercase', opacity:0.8}}>{label}</div>
                </div>
            </div>
         </div>

         {/* Right: Key Metrics & Advice */}
         <div className="dash-card">
            <div className="dash-title">
                <ShieldCheck size={18} className="text-blue-600"/>
                策略建议 (AI Derived)
            </div>
            
            <div className="advice-list">
                <div className={`advice-item`}>
                    <div className="advice-icon">{icon}</div>
                    <div className="advice-text">
                        <strong>建议仓位</strong>
                        {positionAdvice}
                    </div>
                </div>
                <div className="advice-item">
                    <div className="advice-icon"><Activity size={18} className="text-gray-500"/></div>
                    <div className="advice-text">
                        <strong>当前策略</strong>
                        {strategy}
                    </div>
                </div>
                 <div className="advice-item">
                    <div className="advice-icon"><Thermometer size={18} className="text-gray-500"/></div>
                    <div className="advice-text">
                        <strong>市场温度</strong>
                        {score > 50 ? "偏暖" : "偏冷"}
                    </div>
                </div>
            </div>
         </div>
         
      </div>

      {/* Middle: AI Summary */}
      <div className="dash-card" style={{marginTop:'24px'}}>
         <div className="dash-title">
            <Zap size={18} style={{fill:'#ffbb00', stroke:'none'}}/>
            AI 深度点评
         </div>
         <div style={{
             background: '#fcfcfc', 
             borderLeft: `4px solid ${currentColor}`, 
             padding: '16px', 
             borderRadius: '0 8px 8px 0',
             color: '#4b5563',
             lineHeight: 1.6,
             fontSize: '0.95rem'
         }}>
             {is_placeholder ? <span className="italic text-gray-400">数据生成中...</span> : summary}
         </div>
      </div>

      {/* Bottom: History Chart */}
      <div className="dash-card" style={{marginTop:'24px'}}>
         <div className="dash-title">
            <TrendingUp size={18} className="text-blue-500"/>
            最近 7 日情绪走势
         </div>
         <div className="chart-container">
             {renderHistoryChart()}
         </div>
      </div>

    </div>
  );
};

export default SentimentDashboard;
