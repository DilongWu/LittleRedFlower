import React from 'react';
import { TrendingUp, TrendingDown, BarChart2 } from 'lucide-react';
import { formatChange, getChangeColor, getChangeBgColor } from '../../utils/parseRawData';

/**
 * Sector Performance Card - displays leading gainers and losers
 */
const SectorPerformance = ({ sectors }) => {
  if (!sectors || (sectors.gainers.length === 0 && sectors.losers.length === 0 && sectors.concepts.length === 0)) {
    return (
      <div className="ds-card sector-performance-card">
        <div className="ds-card-header">
          <BarChart2 size={18} className="text-purple-500" />
          <span>板块表现</span>
        </div>
        <div className="ds-card-empty">暂无板块数据</div>
      </div>
    );
  }

  return (
    <div className="ds-card sector-performance-card">
      <div className="ds-card-header">
        <BarChart2 size={18} className="text-purple-500" />
        <span>板块表现</span>
      </div>
      <div className="ds-card-content">
        <div className="sector-columns">
          {/* Gainers Column */}
          <div className="sector-column">
            <div className="sector-column-header gainers">
              <TrendingUp size={14} />
              <span>领涨行业</span>
            </div>
            <div className="sector-list">
              {sectors.gainers.slice(0, 5).map((sector, i) => (
                <div key={i} className={`sector-item ${getChangeBgColor(sector.change)}`}>
                  <span className="sector-name">{sector.name}</span>
                  <span className={`sector-change ${getChangeColor(sector.change)}`}>
                    {formatChange(sector.change)}
                  </span>
                  {sector.leadingStock && (
                    <span className="sector-lead-stock" title={`领涨: ${sector.leadingStock}`}>
                      {sector.leadingStock}
                    </span>
                  )}
                </div>
              ))}
              {sectors.gainers.length === 0 && (
                <div className="sector-empty">暂无数据</div>
              )}
            </div>
          </div>

          {/* Losers Column */}
          <div className="sector-column">
            <div className="sector-column-header losers">
              <TrendingDown size={14} />
              <span>领跌行业</span>
            </div>
            <div className="sector-list">
              {sectors.losers.slice(0, 5).map((sector, i) => (
                <div key={i} className={`sector-item ${getChangeBgColor(sector.change)}`}>
                  <span className="sector-name">{sector.name}</span>
                  <span className={`sector-change ${getChangeColor(sector.change)}`}>
                    {formatChange(sector.change)}
                  </span>
                  {sector.leadingStock && (
                    <span className="sector-lead-stock" title={`领跌: ${sector.leadingStock}`}>
                      {sector.leadingStock}
                    </span>
                  )}
                </div>
              ))}
              {sectors.losers.length === 0 && (
                <div className="sector-empty">暂无数据</div>
              )}
            </div>
          </div>
        </div>

        {/* Concepts */}
        {sectors.concepts.length > 0 && (
          <div className="concepts-section">
            <div className="concepts-header">
              <span>领涨概念</span>
            </div>
            <div className="concepts-list">
              {sectors.concepts.slice(0, 5).map((concept, i) => (
                <div key={i} className="concept-tag">
                  <span className="concept-name">{concept.name}</span>
                  <span className={`concept-change ${getChangeColor(concept.change)}`}>
                    {formatChange(concept.change)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SectorPerformance;
