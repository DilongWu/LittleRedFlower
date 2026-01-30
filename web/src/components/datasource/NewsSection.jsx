import React, { useState } from 'react';
import { Newspaper, ChevronDown, ChevronUp } from 'lucide-react';

/**
 * News Section - displays market news with expand/collapse
 */
const NewsSection = ({ news }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const displayCount = isExpanded ? news.length : 10;

  if (!news || news.length === 0) {
    return (
      <div className="ds-card news-section-card">
        <div className="ds-card-header">
          <Newspaper size={18} className="text-indigo-500" />
          <span>市场资讯</span>
        </div>
        <div className="ds-card-empty">暂无资讯数据</div>
      </div>
    );
  }

  return (
    <div className="ds-card news-section-card">
      <div className="ds-card-header">
        <Newspaper size={18} className="text-indigo-500" />
        <span>市场资讯</span>
        <span className="news-count">{news.length}条</span>
        {news.length > 10 && (
          <button
            className="expand-btn"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <>
                <ChevronUp size={14} />
                收起
              </>
            ) : (
              <>
                <ChevronDown size={14} />
                展开全部
              </>
            )}
          </button>
        )}
      </div>
      <div className="ds-card-content">
        <div className="news-list">
          {news.slice(0, displayCount).map((item, i) => (
            <div key={i} className="news-item">
              <span className="news-bullet">•</span>
              <span className="news-title">{item.title}</span>
            </div>
          ))}
        </div>
        {!isExpanded && news.length > 10 && (
          <div className="news-more-hint">
            还有 {news.length - 10} 条资讯...
          </div>
        )}
      </div>
    </div>
  );
};

export default NewsSection;
