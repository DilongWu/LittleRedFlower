/**
 * Frontend data cache with automatic expiration, prefetching, timeout, retry,
 * and stale-while-revalidate support.
 */

const CACHE_DURATION = 10 * 60 * 1000; // 10 minutes (increased from 5)
const REQUEST_TIMEOUT = 15000; // 15 seconds timeout
const MAX_RETRIES = 2; // Maximum retry attempts

// In-memory cache
const cache = new Map();

// Pending requests to avoid duplicate fetches
const pending = new Map();

/**
 * Fetch with timeout support
 */
async function fetchWithTimeout(url, options = {}, timeout = REQUEST_TIMEOUT) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('请求超时，请检查网络连接');
    }
    throw error;
  }
}

/**
 * Fetch with automatic retry on failure
 */
async function fetchWithRetry(url, options = {}, retries = MAX_RETRIES) {
  let lastError;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetchWithTimeout(url, options);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      return response;
    } catch (error) {
      lastError = error;

      // Don't retry on 4xx errors (client errors)
      if (error.message.includes('HTTP 4')) {
        throw error;
      }

      // Wait before retrying (exponential backoff)
      if (attempt < retries) {
        const delay = Math.min(1000 * Math.pow(2, attempt), 5000);
        console.log(`[Retry ${attempt + 1}/${retries}] ${url} - waiting ${delay}ms`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}

/**
 * Get data from cache or fetch from API.
 * Supports stale-while-revalidate: returns stale data immediately while
 * refreshing in the background (within a grace period).
 */
export async function fetchWithCache(url, options = {}) {
  const cacheKey = url;
  const now = Date.now();
  const STALE_GRACE = 5 * 60 * 1000; // 5 minutes grace period for stale data

  // Check if we have valid cached data
  if (cache.has(cacheKey)) {
    const entry = cache.get(cacheKey);
    if (now < entry.expiresAt) {
      console.log(`[Cache HIT] ${url}`);
      return entry.data;
    }

    // Stale but within grace period: return stale data and revalidate in background
    if (now < entry.expiresAt + STALE_GRACE) {
      console.log(`[Cache STALE] ${url} — revalidating in background`);
      // Background revalidate (don't await)
      if (!pending.has(cacheKey)) {
        const bgFetch = fetchWithRetry(url, options)
          .then(async (res) => {
            const data = await res.json();
            cache.set(cacheKey, {
              data,
              expiresAt: Date.now() + CACHE_DURATION,
              fetchedAt: Date.now(),
            });
            pending.delete(cacheKey);
          })
          .catch((err) => {
            console.warn('Background refresh failed for', cacheKey, err);
            pending.delete(cacheKey);
          });
        pending.set(cacheKey, bgFetch);
      }
      return entry.data;
    }

    // Cache fully expired, remove it
    cache.delete(cacheKey);
  }

  // Check if there's already a pending request for this URL
  if (pending.has(cacheKey)) {
    console.log(`[Cache PENDING] ${url}`);
    return pending.get(cacheKey);
  }

  // Fetch new data with retry logic
  console.log(`[Cache MISS] ${url}`);
  const fetchPromise = fetchWithRetry(url, options)
    .then(async (res) => {
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
      console.error(`[Fetch Error] ${url}:`, err.message);
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
  DASHBOARD_ALL: '/api/dashboard/all',
  INDEX_OVERVIEW: '/api/index/overview',
  MARKET_RADAR: '/api/market/radar',
  FUND_FLOW: '/api/fund/flow',
  HOT_CONCEPTS: '/api/concepts/hot',
  RISK_ALERTS: '/api/market/risk',
  SENTIMENT: '/api/sentiment',
};

/**
 * Prefetch all dashboard data (uses aggregated endpoint to reduce requests)
 */
export function prefetchDashboardData() {
  prefetchAll([
    API_ENDPOINTS.DASHBOARD_ALL,
    API_ENDPOINTS.SENTIMENT,
  ]);
}
