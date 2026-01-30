import React, { useState } from 'react';
import { Rocket, ChevronDown, ChevronRight, Sparkles, Newspaper, Clock, AlertTriangle } from 'lucide-react';

/**
 * Enhanced Limit-Up Ladder - displays limit-up stocks with AI analysis and news
 */
const LimitUpLadderEnhanced = ({ ladder }) => {
  const [expandedStocks, setExpandedStocks] = useState(new Set());

  const toggleStock = (index) => {
    setExpandedStocks(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  if (!ladder || ladder.length === 0) {
    return (
      <div className="ds-card ladder-card">
        <div className="ds-card-header">
          <Rocket size={18} className="text-red-500" />
          <span>涨停梯队</span>
        </div>
        <div className="ds-card-empty">暂无涨停数据</div>
      </div>
    );
  }

  // Group by board count
  const boardGroups = {};
  ladder.forEach(stock => {
    const boards = stock.boards;
    if (!boardGroups[boards]) {
      boardGroups[boards] = [];
    }
    boardGroups[boards].push(stock);
  });

  // Sort groups by board count (descending)
  const sortedGroups = Object.entries(boardGroups)
    .sort((a, b) => parseInt(b[0]) - parseInt(a[0]));

  return (
    <div className="ds-card ladder-card">
      <div className="ds-card-header">
        <Rocket size={18} className="text-red-500" />
        <span>涨停梯队</span>
        <span className="ladder-count">{ladder.length}只</span>
      </div>
      <div className="ds-card-content">
        <div className="ladder-groups">
          {sortedGroups.map(([boardCount, stocks], groupIdx) => (
            <div key={groupIdx} className="ladder-group">
              <div className={`ladder-group-header ${parseInt(boardCount) >= 3 ? 'hot' : ''}`}>
                <span className="board-badge">{boardCount}连板</span>
                <span className="stock-count">{stocks.length}只</span>
              </div>
              <div className="ladder-stocks">
                {stocks.map((stock, stockIdx) => {
                  const globalIdx = `${groupIdx}-${stockIdx}`;
                  const isExpanded = expandedStocks.has(globalIdx);
                  const hasDetails = stock.analysis || (stock.news && stock.news.length > 0);

                  return (
                    <div key={stockIdx} className="ladder-stock-item">
                      <div
                        className={`stock-main ${hasDetails ? 'clickable' : ''}`}
                        onClick={() => hasDetails && toggleStock(globalIdx)}
                      >
                        <div className="stock-info">
                          {hasDetails && (
                            isExpanded ?
                              <ChevronDown size={14} className="expand-icon" /> :
                              <ChevronRight size={14} className="expand-icon" />
                          )}
                          <span className="stock-name">{stock.name}</span>
                          <span className="stock-industry">{stock.industry}</span>
                        </div>
                        <div className="stock-meta">
                          {stock.firstLockTime && (
                            <span className="meta-item" title="首次封板时间">
                              <Clock size={12} />
                              {stock.firstLockTime}
                            </span>
                          )}
                          {stock.breakCount > 0 && (
                            <span className="meta-item warning" title="炸板次数">
                              <AlertTriangle size={12} />
                              炸{stock.breakCount}次
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Expandable Details */}
                      {isExpanded && hasDetails && (
                        <div className="stock-details">
                          {/* AI Analysis */}
                          {stock.analysis && (
                            <div className="ai-analysis">
                              <div className="detail-header">
                                <Sparkles size={14} className="text-purple-500" />
                                <span>AI 分析</span>
                                {stock.analysis.tags && Object.keys(stock.analysis.tags).length > 0 && (
                                  <div className="analysis-tags">
                                    {Object.entries(stock.analysis.tags).map(([key, value], i) => (
                                      <span key={i} className="analysis-tag">
                                        {key}: {value}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                              <p className="analysis-text">{stock.analysis.text}</p>
                            </div>
                          )}

                          {/* Related News */}
                          {stock.news && stock.news.length > 0 && (
                            <div className="related-news">
                              <div className="detail-header">
                                <Newspaper size={14} className="text-blue-500" />
                                <span>相关资讯</span>
                              </div>
                              <div className="news-items">
                                {stock.news.map((newsItem, ni) => (
                                  <div key={ni} className="news-item-detail">
                                    <span className="news-title">{newsItem.title}</span>
                                    {newsItem.summary && (
                                      <span className="news-summary">{newsItem.summary}...</span>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default LimitUpLadderEnhanced;
