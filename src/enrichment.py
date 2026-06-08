import logging
import re
import requests
import time
import json
from typing import List, Dict, Optional
from urllib.parse import urlparse

log = logging.getLogger(__name__)

APIFY_BASE = "https://api.apify.com/v2"
GOOGLE_SEARCH_ACTOR = "apify~google-search-scraper"


def enrich_startups(startups: List[Dict[str, str]], cfg) -> List[Dict[str, Optional[str]]]:
    enriched = []
    for startup in startups:
        result = enrich_single(startup, cfg)
        enriched.append(result)
        time.sleep(1)
    found = sum(1 for e in enriched if e.get("founder_name"))
    log.info(f"Enriched {found}/{len(enriched)} startups with founder info")
    return enriched


def enrich_single(startup: Dict[str, str], cfg) -> Dict[str, Optional[str]]:
    name = startup.get("name", "")
    if not name:
        return {**startup, "founder_name": None, "founder_email": None}

    if cfg.apify_api_key:
        result = _search_apify(startup, cfg)
        if result.get("founder_name"):
            return result

    if cfg.apollo_api_key:
        result = _search_apollo(startup, cfg)
        if result.get("founder_name"):
            return result

    return {**startup, "founder_name": None, "founder_email": None}


def _search_apify(startup: Dict[str, str], cfg) -> Dict[str, Optional[str]]:
    name = startup.get("name", "")
    log.info(f"Searching Apify for {name}")

    try:
        result = _run_google_search(name, cfg)
        if result:
            return result
    except Exception as e:
        log.warning(f"Apify search failed for {name}: {e}")

    return {**startup, "founder_name": None, "founder_email": None}


def _run_google_search(query: str, cfg) -> Optional[Dict[str, Optional[str]]]:
    queries = f'"{query}" founder\n"{query}" linkedin\n"{query}" crunchbase'
    resp = requests.post(
        f"{APIFY_BASE}/acts/{GOOGLE_SEARCH_ACTOR}/runs",
        headers={"Authorization": f"Bearer {cfg.apify_api_key}", "Content-Type": "application/json"},
        json={
            "queries": queries,
            "maxPagesPerQuery": 1,
            "resultsPerPage": 5,
            "countryCode": "US",
            "languageCode": "en",
        },
        timeout=60,
    )
    if resp.status_code != 201:
        log.debug(f"Apify run start failed: {resp.status_code}")
        return None

    run_id = resp.json()["data"]["id"]
    log.debug(f"Apify run {run_id} started for: {query}")

    dataset_id = None
    for _ in range(30):
        time.sleep(2)
        status_resp = requests.get(
            f"{APIFY_BASE}/acts/{GOOGLE_SEARCH_ACTOR}/runs/{run_id}",
            headers={"Authorization": f"Bearer {cfg.apify_api_key}"},
        )
        if status_resp.status_code != 200:
            continue
        data = status_resp.json()["data"]
        status = data["status"]
        if status == "SUCCEEDED":
            dataset_id = data.get("defaultDatasetId")
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            log.info(f"Apify run {run_id} {status}: {data.get('errorMessage','')}")
            return None
    else:
        log.info(f"Apify run {run_id} timed out waiting")
        return None

    if not dataset_id:
        log.info(f"Apify: no dataset for run {run_id}")
        return None

    dataset_resp = requests.get(
        f"{APIFY_BASE}/datasets/{dataset_id}/items",
        headers={"Authorization": f"Bearer {cfg.apify_api_key}"},
    )
    if dataset_resp.status_code != 200:
        log.info(f"Apify dataset fetch failed: {dataset_resp.status_code}")
        return None

    items = dataset_resp.json()
    if not items or (isinstance(items, dict) and "error" in items):
        log.info(f"Apify: empty or error dataset for {query}: {items if isinstance(items, dict) else 'empty'}")
        return None

    if isinstance(items, dict):
        log.info(f"Apify: unexpected dataset format for {query}: {list(items.keys())}")
        return None

    result = _parse_google_results(items, query)
    if not result:
        log.info(f"Apify: no founder parsed for {query} (got {len(items)} result items)")
    return result


def _parse_google_results(items: List[Dict], startup_name: str) -> Optional[Dict[str, Optional[str]]]:
    found_name = None
    found_email = None

    results = []
    for item in items:
        raw = item.get("organicResults") or item.get("results") or item.get("items") or []
        if raw:
            results.extend(raw)
        else:
            results.append(item)

    log.debug(f"Parsing {len(results)} search results for {startup_name}")
    if not results and items:
        log.debug(f"Raw item keys: {list(items[0].keys())[:10]}")

    for r in results:
        title = r.get("title", "")
        snippet = r.get("text", "") or r.get("description", "") or r.get("snippet", "") or ""
        url = r.get("url", "") or r.get("link", "") or ""
        combined = f"{title} {snippet}".lower()

        name_match = re.search(
            r"(?:founder|co-founder|ceo|president|owner)\s*[:\-–•·]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
            f"{title} {snippet}"
        )
        if not name_match:
            name_match = re.search(
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s*[:\-–•·]\s*(?:founder|co-founder|ceo|president)",
                f"{title} {snippet}"
            )
        if not name_match:
            name_match = re.search(
                r"(?:by|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s*[|\-–]",
                f"{title}"
            )

        if name_match:
            candidate = name_match.group(1).strip()
            if len(candidate) > 5 and " " in candidate and candidate.lower() != startup_name.lower():
                found_name = candidate

        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', f"{title} {snippet}")
        if email_match:
            found_email = email_match.group(0)

        if "linkedin.com/in/" in url:
            linkedin_name = url.split("linkedin.com/in/")[-1].split("/")[0].split("?")[0]
            linkedin_name = linkedin_name.replace("-", " ").replace("_", " ").title()
            if not found_name:
                found_name = linkedin_name

        if "crunchbase.com" in url and not found_name:
            import re as _re2
            cb_name = _re2.search(r"crunchbase\.com/(?:organization|person)/([^/#?]+)", url)
            if cb_name:
                parsed = cb_name.group(1).replace("-", " ").replace("_", " ").title()
                if len(parsed) > 5 and " " in parsed:
                    found_name = parsed

    if found_name:
        log.info(f"  Apify found: {found_name} ({found_email or 'no email'})")
        return {"founder_name": found_name, "founder_email": found_email}

    log.debug(f"Apify: no founder found for {startup_name}")
    return None


def _search_apollo(startup: Dict[str, str], cfg) -> Dict[str, Optional[str]]:
    domain = _extract_domain(startup)
    if domain:
        return _apollo_by_domain(startup, domain, cfg)
    return _apollo_by_name(startup, cfg)


def _extract_domain(startup: Dict[str, str]) -> Optional[str]:
    raw = startup.get("url", "") or ""
    domain = urlparse(raw).netloc or ""
    known_platforms = {"producthunt.com", "betalist.com", "techcrunch.com",
                       "www.producthunt.com", "feeds.feedburner.com"}
    if domain and domain not in known_platforms:
        return domain
    desc = startup.get("description", "") or ""
    urls = re.findall(r'https?://(?:www\.)?([a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.[a-z]{2,}(?:\.[a-z]{2,})?)', desc, re.I)
    for u in urls:
        if u not in known_platforms and u.count(".") <= 3:
            return u
    return None


def _apollo_by_domain(startup: Dict[str, str], domain: str, cfg) -> Dict[str, Optional[str]]:
    try:
        resp = requests.post(
            "https://api.apollo.io/api/v1/people/match",
            headers={"Content-Type": "application/json", "Cache-Control": "no-cache", "X-Api-Key": cfg.apollo_api_key},
            json={"domain": domain},
            timeout=30,
        )
        if resp.status_code in (403, 429):
            return {**startup, "founder_name": None, "founder_email": None}
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.debug(f"Apollo error for {domain}: {e}")
        return {**startup, "founder_name": None, "founder_email": None}

    person = data.get("person") or (data.get("people", [{}])[0] if data.get("people") else None)
    if not person:
        return _apollo_by_name(startup, cfg)

    name = person.get("name") or ""
    if not name:
        name = (person.get("first_name", "") + " " + person.get("last_name", "")).strip()
    email = person.get("email") or None
    name = name or None

    if name:
        log.info(f"  Apollo found: {name} ({email or 'no email'}) @ {domain}")
    return {**startup, "founder_name": name, "founder_email": email}


def _apollo_by_name(startup: Dict[str, str], cfg) -> Dict[str, Optional[str]]:
    name = startup.get("name", "")
    if not name:
        return {**startup, "founder_name": None, "founder_email": None}
    try:
        resp = requests.post(
            "https://api.apollo.io/api/v1/mixed_people/search",
            headers={"Content-Type": "application/json", "X-Api-Key": cfg.apollo_api_key},
            json={"q_organization_name": name, "page": 1, "per_page": 3},
            timeout=30,
        )
        if resp.status_code in (403, 429):
            return {**startup, "founder_name": None, "founder_email": None}
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.debug(f"Apollo name search error for {name}: {e}")
        return {**startup, "founder_name": None, "founder_email": None}

    people = data.get("people") or data.get("contacts") or []
    if not people:
        return {**startup, "founder_name": None, "founder_email": None}

    person = people[0]
    pname = person.get("name") or ""
    if not pname:
        pname = (person.get("first_name", "") + " " + person.get("last_name", "")).strip()
    email = person.get("email") or None
    pname = pname or None

    if pname:
        log.info(f"  Apollo found: {pname} ({email or 'no email'}) @ {name}")
    return {**startup, "founder_name": pname, "founder_email": email}
