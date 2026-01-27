import React from 'react';

const SectorHeatmap = ({ sectors }) => {
  if (!sectors || sectors.length === 0) return <div className="text-gray-400">暂无板块数据</div>;

  // 1. Sort by change percentage
  const sortedSectors = [...sectors].sort((a, b) => b.change - a.change);
  
  // 2. Filter interesting ones (Top 15 gainers and Top 15 losers for better viz)
  // Or just show top 30 mixed? Let's show separate groups or a mixed grid.
  // A simple grid of boxes.
  
  const renderBox = (item) => {
    const change = item.change;
    let bgColor = '#f3f4f6';
    let textColor = '#1f2937';
    
    // Color Intensity Logic
    if (change >= 0) {
        // Red intensity
        if (change > 5) bgColor = '#b91c1c';
        else if (change > 3) bgColor = '#ef4444';
        else if (change > 1) bgColor = '#f87171';
        else bgColor = '#fecaca';
        
        if (change > 1) textColor = 'white';
    } else {
        // Green intensity (Chinese style)
        if (change < -5) bgColor = '#15803d';
        else if (change < -3) bgColor = '#22c55e';
        else if (change < -1) bgColor = '#4ade80';
        else bgColor = '#bbf7d0';
        
        if (change < -1) textColor = 'white';
    }

    return (
        <div 
          key={item.name}
          className="heatmap-box"
          style={{ backgroundColor: bgColor, color: textColor }}
          title={`${item.name} ${change}%`}
        >
           <div className="box-name">{item.name}</div>
           <div className="box-val">{change > 0 ? '+' : ''}{change.toFixed(2)}%</div>
           <div className="box-lead">{item.top_stock}</div>
        </div>
    );
  };

  return (
    <div className="heatmap-container">
        <h4 className="radar-subtitle">📈 领涨板块 (Top Gainers)</h4>
        <div className="heatmap-grid">
            {sortedSectors.slice(0, 16).map(renderBox)}
        </div>
        
        <h4 className="radar-subtitle" style={{marginTop: '20px'}}>📉 领跌板块 (Top Losers)</h4>
        <div className="heatmap-grid">
            {sortedSectors.slice(sortedSectors.length - 16).reverse().map(renderBox)}
        </div>
    </div>
  );
};

export default SectorHeatmap;
