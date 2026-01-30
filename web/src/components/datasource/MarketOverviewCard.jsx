import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { formatChange, getChangeColor } from '../../utils/parseRawData';

/**
 * Market Overview Card - displays index data (上证/深证/创业板)
 */
const MarketOverviewCard = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="ds-card market-overview-card">
        <div className="ds-card-header">
          <TrendingUp size={18} className="text-blue-500" />
          <span>市场行情</span>
        </div>
        <div className="ds-card-empty">暂无行情数据</div>
      </div>
    );
  }

  return (
    <div className="ds-card market-overview-card">
      <div className="ds-card-header">
        <TrendingUp size={18} className="text-blue-500" />
        <span>市场行情</span>
      </div>
      <div className="ds-card-content">
        {data.map((index, i) => {
          const isUp = index.change > 0;
          const isDown = index.change < 0;
          const Icon = isUp ? TrendingUp : isDown ? TrendingDown : Minus;

          return (
            <div key={i} className="index-item">
              <div className="index-name">{index.name}</div>
              <div className={`index-value ${getChangeColor(index.change)}`}>
                {index.value.toFixed(2)}
              </div>
              <div className={`index-change ${getChangeColor(index.change)}`}>
                <Icon size={14} />
                <span>{formatChange(index.change)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MarketOverviewCard;
