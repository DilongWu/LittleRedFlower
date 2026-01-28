/**
 * Frontend data cache with automatic expiration and prefetching
 */

const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

// In-memory cache
const cache = new Map();

// Pending requests to avoid duplicate fetches
const pending = new Map();

/**
 * Get data from cache or fetch from API
 */
export async function fetchWithCache(url, options = {}) {
  const cacheKey = url;
  const now = Date.now();

  // Check if we have valid cached data
  if (cache.has(cacheKey)) {
    const entry = cache.get(cacheKey);
    if (now < entry.expiresAt) {
      console.log(`[Cache HIT] ${url}`);
      return entry.data;
    }
    // Cache expired, remove it
    cache.delete(cacheKey);
  }

  // Check if there's already a pending request for this URL
  if (pending.has(cacheKey)) {
    console.log(`[Cache PENDING] ${url}`);
    return pending.get(cacheKey);
  }

  // Fetch new data
  console.log(`[Cache MISS] ${url}`);
  const fetchPromise = fetch(url, options)
    .then(async (res) => {
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();

      // Store in cache
      cache.set(cacheKey, {
        data,
        expiresAt: now + CACHE_DURATION,
        fetchedAt: now,
      });

      // Remove from pending
      pending.delete(cacheKey);

      return data;
    })
    .catch((err) => {
      pending.delete(cacheKey);
      throw err;
    });

  // Store the pending promise
  pending.set(cacheKey, fetchPromise);

  return fetchPromise;
}

/**
 * Prefetch multiple URLs in background
 */
export function prefetchAll(urls) {
  urls.forEach((url) => {
    // Only prefetch if not already cached or pending
    if (!cache.has(url) && !pending.has(url)) {
      fetchWithCache(url).catch(() => {
        // Silently ignore prefetch errors
      });
    }
  });
}

/**
 * Clear all cache
 */
export function clearCache() {
  cache.clear();
}

/**
 * Get cache stats
 */
export function getCacheStats() {
  const now = Date.now();
  let valid = 0;
  let expired = 0;

  cache.forEach((entry) => {
    if (now < entry.expiresAt) {
      valid++;
    } else {
      expired++;
    }
  });

  return {
    total: cache.size,
    valid,
    expired,
    pending: pending.size,
  };
}

// API endpoints to prefetch
export const API_ENDPOINTS = {
  INDEX_OVERVIEW: '/api/index/overview',
  MARKET_RADAR: '/api/market/radar',
  FUND_FLOW: '/api/fund/flow',
  HOT_CONCEPTS: '/api/concepts/hot',
  RISK_ALERTS: '/api/market/risk',
  SENTIMENT: '/api/sentiment',
};

/**
 * Prefetch all dashboard data
 */
export function prefetchDashboardData() {
  prefetchAll([
    API_ENDPOINTS.INDEX_OVERVIEW,
    API_ENDPOINTS.MARKET_RADAR,
    API_ENDPOINTS.FUND_FLOW,
    API_ENDPOINTS.HOT_CONCEPTS,
    API_ENDPOINTS.SENTIMENT,
  ]);
}
