/**
 * Parse raw_data text from daily/weekly reports into structured JSON
 */

/**
 * Parse index data like "上证指数: 4139.90 (0.18%)"
 */
function parseIndexLine(line) {
  const match = line.match(/^(.+?):\s*([\d.]+)\s*\(([-+]?[\d.]+)%\)/);
  if (match) {
    return {
      name: match[1].trim(),
      value: parseFloat(match[2]),
      change: parseFloat(match[3])
    };
  }
  return null;
}

/**
 * Parse turnover line like "沪深两市总成交额: 1.52万亿元"
 */
function parseTurnoverLine(line) {
  // Match patterns like "1.52万亿元" or "1万亿元" or "9800亿元"
  const match = line.match(/([\d.]+)(万亿|亿)元/);
  if (match) {
    const value = parseFloat(match[1]);
    const unit = match[2];
    return {
      value,
      unit,
      display: `${value}${unit}元`
    };
  }
  return null;
}

/**
 * Parse sector line like "- 化工: 5.20% (领涨股: 某某某)"
 */
function parseSectorLine(line) {
  const trimmed = line.replace(/^[-•]\s*/, '').trim();

  // Pattern: "板块名称: 涨跌幅% (领涨股: 股票名)"
  const match = trimmed.match(/^(.+?):\s*([-+]?[\d.]+)%\s*(?:\(领涨股:\s*(.+?)\))?/);
  if (match) {
    return {
      name: match[1].trim(),
      change: parseFloat(match[2]),
      leadingStock: match[3] ? match[3].trim() : null
    };
  }

  // Simpler pattern without leading stock
  const simpleMatch = trimmed.match(/^(.+?):\s*([-+]?[\d.]+)%/);
  if (simpleMatch) {
    return {
      name: simpleMatch[1].trim(),
      change: parseFloat(simpleMatch[2]),
      leadingStock: null
    };
  }

  return null;
}

/**
 * Parse limit-up stock line like "- 白银有色 (7连板): 行业-有色金属, 首次封板-100220, 最后封板-103000, 炸板-2次"
 */
function parseLimitUpStockLine(line) {
  const trimmed = line.replace(/^[-•]\s*/, '').trim();

  // Pattern: "股票名 (N连板): 行业-xxx, 首次封板-xxx, 最后封板-xxx, 炸板-N次"
  const match = trimmed.match(/^(.+?)\s*\((\d+)连板\):\s*行业-(.+?),\s*首次封板-(\d+),\s*最后封板-(\d+),\s*炸板-(\d+)次/);
  if (match) {
    // Format time like 100220 -> 10:02:20
    const formatTime = (t) => {
      const s = t.toString().padStart(6, '0');
      return `${s.slice(0, 2)}:${s.slice(2, 4)}:${s.slice(4, 6)}`;
    };

    return {
      name: match[1].trim(),
      boards: parseInt(match[2]),
      industry: match[3].trim(),
      firstLockTime: formatTime(match[4]),
      lastLockTime: formatTime(match[5]),
      breakCount: parseInt(match[6]),
      analysis: null,
      news: []
    };
  }

  return null;
}

/**
 * Parse AI analysis line like "    * AI分析: [板块:有色金属][首封:10:02:20] 分析内容..."
 */
function parseAIAnalysisLine(line) {
  const trimmed = line.trim();
  if (trimmed.startsWith('* AI分析:') || trimmed.startsWith('*AI分析:')) {
    const content = trimmed.replace(/^\*\s*AI分析:\s*/, '');

    // Extract metadata tags like [板块:xxx][首封:xx:xx:xx]
    const tags = {};
    const tagMatches = content.matchAll(/\[(.+?):(.+?)\]/g);
    for (const tm of tagMatches) {
      tags[tm[1]] = tm[2];
    }

    // Get analysis text after tags
    const analysisText = content.replace(/\[.+?:.+?\]/g, '').trim();

    return {
      tags,
      text: analysisText
    };
  }
  return null;
}

/**
 * Parse news line like "    * 资讯: 标题 (摘要: 内容...)"
 */
function parseNewsLine(line) {
  const trimmed = line.trim();
  if (trimmed.startsWith('* 资讯:') || trimmed.startsWith('*资讯:')) {
    const content = trimmed.replace(/^\*\s*资讯:\s*/, '');

    // Try to extract title and summary
    const match = content.match(/^(.+?)\s*\(摘要:\s*(.+?)\.\.\.\)$/);
    if (match) {
      return {
        title: match[1].trim(),
        summary: match[2].trim()
      };
    }

    return {
      title: content,
      summary: null
    };
  }
  return null;
}

/**
 * Main parsing function
 * @param {string} rawData - The raw_data text from report JSON
 * @param {object} sentiment - Optional sentiment data to merge
 * @returns {object} Structured data object
 */
export function parseRawData(rawData, sentiment = null) {
  if (!rawData) {
    return {
      marketOverview: [],
      turnover: null,
      turnoverChange: null,
      sectors: { gainers: [], losers: [], concepts: [] },
      news: [],
      ladder: [],
      sentiment: sentiment
    };
  }

  const lines = rawData.split('\n');
  const result = {
    marketOverview: [],
    turnover: null,
    turnoverChange: null,
    sectors: { gainers: [], losers: [], concepts: [] },
    news: [],
    ladder: [],
    sentiment: sentiment
  };

  let currentSection = null;
  let currentSubSection = null;
  let currentStock = null;

  for (const line of lines) {
    const trimmedLine = line.trim();
    if (!trimmedLine) continue;

    // Check for section headers like 【市场行情】
    const sectionMatch = trimmedLine.match(/^【(.*)】$/);
    if (sectionMatch) {
      currentSection = sectionMatch[1];
      currentSubSection = null;
      continue;
    }

    // Parse based on current section
    if (currentSection?.includes('市场行情') || currentSection?.includes('指数表现')) {
      const indexData = parseIndexLine(trimmedLine);
      if (indexData) {
        result.marketOverview.push(indexData);
      }
    }
    else if (currentSection?.includes('成交额')) {
      // Total turnover
      if (trimmedLine.includes('总成交额') || trimmedLine.includes('日均成交额')) {
        const turnover = parseTurnoverLine(trimmedLine);
        if (turnover) {
          result.turnover = turnover;
        }
      }
      // Turnover change
      else if (trimmedLine.includes('放量') || trimmedLine.includes('缩量')) {
        const changeMatch = trimmedLine.match(/(放量|缩量)[:：]?\s*([\d.]+)(万亿|亿)元/);
        if (changeMatch) {
          result.turnoverChange = {
            direction: changeMatch[1],
            value: parseFloat(changeMatch[2]),
            unit: changeMatch[3],
            display: `${changeMatch[1]} ${changeMatch[2]}${changeMatch[3]}元`
          };
        }
      }
    }
    else if (currentSection?.includes('板块表现')) {
      // Check for sub-sections
      if (trimmedLine.includes('领涨行业') || trimmedLine === '领涨行业:') {
        currentSubSection = 'gainers';
        continue;
      }
      if (trimmedLine.includes('领跌行业') || trimmedLine === '领跌行业:') {
        currentSubSection = 'losers';
        continue;
      }
      if (trimmedLine.includes('领涨概念') || trimmedLine === '领涨概念:') {
        currentSubSection = 'concepts';
        continue;
      }

      // Parse sector line
      if (trimmedLine.startsWith('-') || trimmedLine.startsWith('•')) {
        const sector = parseSectorLine(trimmedLine);
        if (sector && currentSubSection) {
          result.sectors[currentSubSection].push(sector);
        } else if (sector) {
          // Default to gainers if no sub-section specified
          result.sectors.gainers.push(sector);
        }
      }
    }
    else if (currentSection?.includes('资讯')) {
      // News items
      if (trimmedLine.startsWith('-') || trimmedLine.startsWith('•')) {
        const newsTitle = trimmedLine.replace(/^[-•]\s*/, '').trim();
        if (newsTitle) {
          result.news.push({ title: newsTitle });
        }
      }
    }
    else if (currentSection?.includes('涨停') || currentSection?.includes('强势股')) {
      // Check if this is a stock header line
      if (trimmedLine.startsWith('-') || trimmedLine.startsWith('•')) {
        const stock = parseLimitUpStockLine(trimmedLine);
        if (stock) {
          // Save previous stock if exists
          if (currentStock) {
            result.ladder.push(currentStock);
          }
          currentStock = stock;
        }
      }
      // Check for AI analysis (indented line)
      else if (line.startsWith('    ') || line.startsWith('\t')) {
        const analysis = parseAIAnalysisLine(trimmedLine);
        if (analysis && currentStock) {
          currentStock.analysis = analysis;
          continue;
        }

        const news = parseNewsLine(trimmedLine);
        if (news && currentStock) {
          currentStock.news.push(news);
        }
      }
    }
  }

  // Don't forget the last stock
  if (currentStock) {
    result.ladder.push(currentStock);
  }

  // Sort ladder by board count (descending)
  result.ladder.sort((a, b) => b.boards - a.boards);

  return result;
}

/**
 * Get color class based on change value
 */
export function getChangeColor(change) {
  if (change > 0) return 'text-red-500';
  if (change < 0) return 'text-green-500';
  return 'text-gray-500';
}

/**
 * Get color class based on change value (background version)
 */
export function getChangeBgColor(change) {
  if (change > 0) return 'bg-red-50 border-red-200';
  if (change < 0) return 'bg-green-50 border-green-200';
  return 'bg-gray-50 border-gray-200';
}

/**
 * Format change with sign
 */
export function formatChange(change) {
  if (change > 0) return `+${change.toFixed(2)}%`;
  return `${change.toFixed(2)}%`;
}

export default parseRawData;
