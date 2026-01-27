import React from 'react';

const LimitUpLadder = ({ ladder }) => {
  if (!ladder || Object.keys(ladder).length === 0) return <div className="text-gray-400">暂无涨停数据</div>;

  // Sort keys descending (High board first)
  const levels = Object.keys(ladder).sort((a, b) => parseInt(b) - parseInt(a));

  return (
    <div className="ladder-container">
        {levels.map(level => (
            <div key={level} className="ladder-level">
                <div className="level-header">
                    <div className="level-badge">{level}连板</div>
                    <div className="level-count">{ladder[level].length} 家</div>
                </div>
                <div className="level-stocks">
                    {ladder[level].map((stock, idx) => (
                        <div key={stock.code} className="stock-pill" title={stock.reason}>
                            <span className="stock-name">{stock.name}</span>
                            <span className="stock-industry">{stock.industry}</span>
                        </div>
                    ))}
                </div>
            </div>
        ))}
    </div>
  );
};

export default LimitUpLadder;
