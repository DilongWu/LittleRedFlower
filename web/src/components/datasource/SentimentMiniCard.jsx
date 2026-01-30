import React from 'react';
import { Activity, TrendingUp, TrendingDown, Minus } from 'lucide-react';

/**
 * Sentiment Mini Card - displays sentiment score and label
 */
const SentimentMiniCard = ({ sentiment }) => {
  if (!sentiment || sentiment.is_placeholder) {
    return (
      <div className="ds-card sentiment-mini-card">
        <div className="ds-card-header">
          <Activity size={18} className="text-orange-500" />
          <span>市场情绪</span>
        </div>
        <div className="ds-card-empty">暂无情绪数据</div>
      </div>
    );
  }

  const { score, label, summary } = sentiment;

  // Determine color and icon based on score
  const getScoreStyle = (s) => {
    if (s >= 61) return { color: 'text-red-500', bgColor: 'bg-red-50', Icon: TrendingUp };
    if (s <= 40) return { color: 'text-green-500', bgColor: 'bg-green-50', Icon: TrendingDown };
    return { color: 'text-yellow-500', bgColor: 'bg-yellow-50', Icon: Minus };
  };

  const { color, bgColor, Icon } = getScoreStyle(score);

  // Calculate progress bar width
  const progressWidth = Math.min(Math.max(score, 0), 100);

  return (
    <div className="ds-card sentiment-mini-card">
      <div className="ds-card-header">
        <Activity size={18} className="text-orange-500" />
        <span>市场情绪</span>
      </div>
      <div className="ds-card-content">
        <div className="sentiment-display">
          <div className={`sentiment-score ${color}`}>
            <Icon size={20} />
            <span className="score-number">{score}</span>
          </div>
          <div className={`sentiment-label ${bgColor}`}>
            {label}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="sentiment-progress">
          <div className="progress-track">
            <div
              className={`progress-fill ${score >= 61 ? 'high' : score <= 40 ? 'low' : 'neutral'}`}
              style={{ width: `${progressWidth}%` }}
            />
          </div>
          <div className="progress-labels">
            <span>恐惧</span>
            <span>中性</span>
            <span>贪婪</span>
          </div>
        </div>

        {/* Summary (truncated) */}
        {summary && (
          <div className="sentiment-summary" title={summary}>
            {summary.length > 80 ? summary.slice(0, 80) + '...' : summary}
          </div>
        )}
      </div>
    </div>
  );
};

export default SentimentMiniCard;
