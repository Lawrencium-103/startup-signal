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
    query_founder = f'"{query}" founder'
    resp = requests.post(
        f"{APIFY_BASE}/acts/{GOOGLE_SEARCH_ACTOR}/runs",
        headers={"Authorization": f"Bearer {cfg.apify_api_key}", "Content-Type": "application/json"},
        json={
            "queries": query_founder,
            "maxPagesPerQuery": 1,
            "resultsPerPage": 5,
            "countryCode": "US",
            "languageCode": "en",
        },
        timeout=30,
    )
    if resp.status_code != 201:
        log.debug(f"Apify run start failed: {resp.status_code}")
        return None

    run_id = resp.json()["data"]["id"]
    log.debug(f"Apify run {run_id} started for: {query}")

    for _ in range(30):
        time.sleep(2)
        status_resp = requests.get(
            f"{APIFY_BASE}/acts/{GOOGLE_SEARCH_ACTOR}/runs/{run_id}",
            headers={"Authorization": f"Bearer {cfg.apify_api_key}"},
        )
        if status_resp.status_code != 200:
            continue
        status = status_resp.json()["data"]["status"]
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            log.debug(f"Apify run {run_id} {status}")
            return None
    else:
        log.debug(f"Apify run {run_id} timed out waiting")
        return None

    dataset_resp = requests.get(
        f"{APIFY_BASE}/acts/{GOOGLE_SEARCH_ACTOR}/runs/{run_id}/dataset/items",
        headers={"Authorization": f"Bearer {cfg.apify_api_key}"},
    )
    if dataset_resp.status_code != 200:
        return None

    items = dataset_resp.json()
    return _parse_google_results(items, query)


def _parse_google_results(items: List[Dict], startup_name: str) -> Optional[Dict[str, Optional[str]]]:
    found_name = None
    found_email = None

    for item in items:
        title = item.get("title", "")
        snippet = item.get("text", "") or item.get("description", "") or ""
        url = item.get("url", "") or ""
        combined = f"{title} {snippet}".lower()

        name_match = re.search(
            r"(?:founder|co-founder|ceo|president)\s*[:\-–]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
            f"{title} {snippet}"
        )
        if not name_match:
            name_match = re.search(
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s*[:\-–]\s*(?:founder|co-founder|ceo)",
                f"{title} {snippet}"
            )

        if name_match:
            candidate = name_match.group(1).strip()
            if len(candidate) > 5 and " " in candidate:
                found_name = candidate

        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', f"{title} {snippet}")
        if email_match:
            found_email = email_match.group(0)

        if "linkedin.com/in/" in url:
            linkedin_name = url.split("linkedin.com/in/")[-1].split("/")[0].split("?")[0]
            linkedin_name = linkedin_name.replace("-", " ").replace("_", " ").title()
            if not found_name:
                found_name = linkedin_name

        if "linkedin.com" in url and "founder" in combined:
            if not found_name:
                pass

    if found_name:
        log.info(f"  Apify found: {found_name} ({found_email or 'no email'})")
        return {"founder_name": found_name, "founder_email": found_email}

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
