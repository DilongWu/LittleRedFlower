import React from 'react';
import { Coins, TrendingUp, TrendingDown } from 'lucide-react';

/**
 * Turnover Card - displays market turnover data
 */
const TurnoverCard = ({ turnover, turnoverChange }) => {
  if (!turnover) {
    return (
      <div className="ds-card turnover-card">
        <div className="ds-card-header">
          <Coins size={18} className="text-yellow-500" />
          <span>成交额</span>
        </div>
        <div className="ds-card-empty">暂无成交数据</div>
      </div>
    );
  }

  const isIncrease = turnoverChange?.direction === '放量';

  return (
    <div className="ds-card turnover-card">
      <div className="ds-card-header">
        <Coins size={18} className="text-yellow-500" />
        <span>成交额</span>
      </div>
      <div className="ds-card-content">
        <div className="turnover-main">
          <span className="turnover-value">{turnover.display}</span>
          <span className="turnover-label">两市总成交</span>
        </div>
        {turnoverChange && (
          <div className={`turnover-change ${isIncrease ? 'increase' : 'decrease'}`}>
            {isIncrease ? (
              <TrendingUp size={14} />
            ) : (
              <TrendingDown size={14} />
            )}
            <span>较前一交易日{turnoverChange.display}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default TurnoverCard;
