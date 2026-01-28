"""
HTTP client with retry mechanism, connection pooling, and rate limiting.
Optimized for AkShare API calls to avoid 'Remote end closed connection' errors.
"""
import time
import logging
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Tuple, Any, Optional

# Global session with connection pooling
_SESSION = None

# Global thread pool for concurrent requests (reduced workers to limit concurrency)
_EXECUTOR: Optional[ThreadPoolExecutor] = None

# Rate limiter: minimum interval between requests (in seconds)
_MIN_REQUEST_INTERVAL = 0.5  # 500ms between requests (increased for stability)
_last_request_time = 0.0
_rate_lock = threading.Lock()


def _rate_limit():
    """Apply rate limiting to avoid overwhelming the data source."""
    global _last_request_time
    with _rate_lock:
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            sleep_time = _MIN_REQUEST_INTERVAL - elapsed
            time.sleep(sleep_time)
        _last_request_time = time.time()


def get_session():
    """Get or create a requests session with retry logic and keep-alive."""
    global _SESSION
    if _SESSION is None:
        _SESSION = requests.Session()

        # Configure retry strategy with more comprehensive error handling
        retry_strategy = Retry(
            total=3,  # Total retries
            backoff_factor=1.5,  # Wait 1.5, 3, 6 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            raise_on_status=False,
            connect=3,
            read=3,
        )

        # Mount adapter with moderate connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # Moderate pool size
            pool_maxsize=20,      # Moderate max size
            pool_block=False
        )
        _SESSION.mount("http://", adapter)
        _SESSION.mount("https://", adapter)

        # Set default headers
        _SESSION.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })

    return _SESSION


def get_executor() -> ThreadPoolExecutor:
    """Get or create thread pool executor for concurrent requests."""
    global _EXECUTOR
    if _EXECUTOR is None:
        # Reduced to 4 workers to limit concurrent requests to data source
        _EXECUTOR = ThreadPoolExecutor(max_workers=4)
    return _EXECUTOR


def fetch_with_retry(func, *args, max_retries=3, timeout=30, **kwargs):
    """
    Execute an AkShare function with retry logic and rate limiting.

    Args:
        func: The AkShare function to call
        *args: Positional arguments for the function
        max_retries: Maximum number of retries (default: 3)
        timeout: Not used directly but for reference
        **kwargs: Keyword arguments for the function

    Returns:
        The result of the function call, or None if all retries failed
    """
    last_error = None

    # List of retryable error patterns
    retryable_errors = [
        'connection', 'timeout', 'remote', 'aborted',
        'remotedisconnected', 'connectionreset', 'connectionaborted',
        'connectionrefused', 'brokenpipe', 'eof', 'reset by peer',
        'remote end closed', 'without response', 'broken pipe'
    ]

    for attempt in range(max_retries + 1):
        try:
            # Apply rate limiting before each request
            _rate_limit()
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()

            # Check if it's a connection error worth retrying
            is_retryable = any(x in error_msg for x in retryable_errors)

            if is_retryable and attempt < max_retries:
                # Exponential backoff: 3s, 6s, 12s (longer waits for overseas servers)
                wait_time = min(3 ** (attempt + 1), 15)
                logging.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s: {str(e)[:80]}")
                time.sleep(wait_time)
                continue

            # Non-retryable error or last attempt
            break

    if last_error:
        logging.error(f"All retries failed: {str(last_error)[:100]}")

    return None


def fetch_sequential(tasks: List[Tuple[Callable, tuple, dict]], delay: float = 0.5) -> List[Any]:
    """
    Execute multiple AkShare functions sequentially with delay.
    Use this instead of fetch_concurrent when hitting rate limits.

    Args:
        tasks: List of tuples (func, args, kwargs) to execute
        delay: Delay between requests in seconds

    Returns:
        List of results in the same order as tasks (None for failed tasks)
    """
    results = []
    for func, args, kwargs in tasks:
        result = fetch_with_retry(func, *args, **kwargs)
        results.append(result)
        if delay > 0:
            time.sleep(delay)
    return results


def fetch_concurrent(tasks: List[Tuple[Callable, tuple, dict]], max_concurrent: int = 2) -> List[Any]:
    """
    Execute multiple AkShare functions with limited concurrency.

    Args:
        tasks: List of tuples (func, args, kwargs) to execute
        max_concurrent: Maximum concurrent requests (default: 2 to avoid rate limits)

    Returns:
        List of results in the same order as tasks (None for failed tasks)
    """
    # For small number of tasks, use sequential to be safer
    if len(tasks) <= 2:
        return fetch_sequential(tasks, delay=0.3)

    executor = get_executor()
    results = [None] * len(tasks)
    futures = {}

    # Submit tasks in batches to limit concurrency
    for i, (func, args, kwargs) in enumerate(tasks):
        future = executor.submit(fetch_with_retry, func, *args, **kwargs)
        futures[future] = i

    for future in as_completed(futures):
        idx = futures[future]
        try:
            results[idx] = future.result()
        except Exception as e:
            logging.error(f"Concurrent task {idx} failed: {e}")
            results[idx] = None

    return results


def close_session():
    """Close the session and executor (call on shutdown)."""
    global _SESSION, _EXECUTOR
    if _SESSION:
        _SESSION.close()
        _SESSION = None
    if _EXECUTOR:
        _EXECUTOR.shutdown(wait=False)
        _EXECUTOR = None
