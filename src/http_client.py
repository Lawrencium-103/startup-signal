import logging
import time
import random
from typing import Optional, Dict

import requests

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})


def safe_get(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    min_delay: float = 2.0,
    max_delay: float = 4.0,
    max_retries: int = 3,
    **kwargs,
) -> Optional[requests.Response]:
    delay = random.uniform(min_delay, max_delay)
    log.debug(f"Rate limit: waiting {delay:.1f}s before {url}")
    time.sleep(delay)

    merged = dict(SESSION.headers)
    if headers:
        merged.update(headers)

    for attempt in range(max_retries):
        try:
            resp = SESSION.get(url, headers=merged, timeout=timeout, **kwargs)

            if resp.status_code == 429 or resp.status_code == 503:
                retry_after = resp.headers.get("Retry-After")
                wait = int(retry_after) if retry_after and retry_after.isdigit() else (2 ** attempt + random.uniform(0, 1))
                log.warning(f"Got {resp.status_code} for {url}, waiting {wait:.1f}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue

            if resp.status_code == 403:
                log.warning(f"Blocked (403) for {url}")
                return None

            resp.raise_for_status()
            return resp

        except requests.exceptions.Timeout:
            log.warning(f"Timeout for {url} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt + random.uniform(0, 1))
            continue

        except requests.exceptions.RequestException as e:
            log.debug(f"Request failed for {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt + random.uniform(0, 1))
                continue
            return None

    return None


def safe_post(
    url: str,
    json_data: dict,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    min_delay: float = 1.0,
    max_delay: float = 2.0,
    max_retries: int = 3,
    **kwargs,
) -> Optional[requests.Response]:
    delay = random.uniform(min_delay, max_delay)
    log.debug(f"Rate limit: waiting {delay:.1f}s before POST {url}")
    time.sleep(delay)

    merged = dict(SESSION.headers)
    if headers:
        merged.update(headers)

    for attempt in range(max_retries):
        try:
            resp = SESSION.post(url, headers=merged, json=json_data, timeout=timeout, **kwargs)

            if resp.status_code == 429 or resp.status_code == 503:
                retry_after = resp.headers.get("Retry-After")
                wait = int(retry_after) if retry_after and retry_after.isdigit() else (2 ** attempt + random.uniform(0, 1))
                log.warning(f"Got {resp.status_code} for POST {url}, waiting {wait:.1f}s")
                time.sleep(wait)
                continue

            resp.raise_for_status()
            return resp

        except requests.exceptions.Timeout:
            log.warning(f"Timeout for POST {url} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt + random.uniform(0, 1))
            continue

        except requests.exceptions.RequestException as e:
            log.debug(f"POST failed for {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt + random.uniform(0, 1))
                continue
            return None

    return None
