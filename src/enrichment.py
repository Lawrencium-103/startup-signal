import logging
import re
import requests
import time
from typing import List, Dict, Optional
from urllib.parse import urlparse

log = logging.getLogger(__name__)


def enrich_startups(startups: List[Dict[str, str]], cfg) -> List[Dict[str, Optional[str]]]:
    if not cfg.apollo_api_key:
        log.info("Apollo API key not configured, skipping enrichment")
        return startups

    enriched = []
    for startup in startups:
        result = enrich_single(startup, cfg)
        enriched.append(result)
        if len(startups) > 1:
            time.sleep(1)

    log.info(f"Enriched {sum(1 for e in enriched if e.get('founder_name'))}/{len(enriched)} startups")
    return enriched


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


def enrich_single(startup: Dict[str, str], cfg) -> Dict[str, Optional[str]]:
    domain = _extract_domain(startup)
    if domain:
        return _search_by_domain(startup, domain, cfg)
    log.debug(f"No valid domain for {startup.get('name')}, trying name search")
    return _search_by_name(startup, cfg)


def _search_by_domain(startup: Dict[str, str], domain: str, cfg) -> Dict[str, Optional[str]]:
    try:
        resp = requests.post(
            "https://api.apollo.io/api/v1/people/match",
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "X-Api-Key": cfg.apollo_api_key,
            },
            json={"domain": domain},
            timeout=30,
        )
        if resp.status_code == 403:
            log.warning(f"Apollo 403 for {domain} — check API key")
            return {**startup, "founder_name": None, "founder_email": None}
        if resp.status_code == 429:
            log.warning(f"Apollo rate limited for {domain}")
            return {**startup, "founder_name": None, "founder_email": None}
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        log.debug(f"Apollo API error for {domain}: {e}")
        return {**startup, "founder_name": None, "founder_email": None}

    person = data.get("person") or (data.get("people", [{}])[0] if data.get("people") else None)
    if not person:
        log.debug(f"No person found at {domain}")
        return _search_by_name(startup, cfg)

    name = person.get("name") or ""
    if not name:
        name = (person.get("first_name", "") + " " + person.get("last_name", "")).strip()
    name = name or None
    email = person.get("email") or None

    if name:
        log.info(f"  Found: {name} ({email or 'no email'}) @ {domain}")
    return {**startup, "founder_name": name, "founder_email": email}


def _search_by_name(startup: Dict[str, str], cfg) -> Dict[str, Optional[str]]:
    name = startup.get("name", "")
    if not name:
        return {**startup, "founder_name": None, "founder_email": None}

    try:
        resp = requests.post(
            "https://api.apollo.io/api/v1/mixed_people/search",
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "X-Api-Key": cfg.apollo_api_key,
            },
            json={
                "q_organization_name": name,
                "page": 1,
                "per_page": 3,
            },
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
        log.debug(f"No Apollo results for {name}")
        return {**startup, "founder_name": None, "founder_email": None}

    person = people[0]
    person_name = person.get("name") or ""
    if not person_name:
        person_name = (person.get("first_name", "") + " " + person.get("last_name", "")).strip()
    email = person.get("email") or None

    if person_name:
        log.info(f"  Found (name search): {person_name} ({email or 'no email'}) @ {name}")
    return {**startup, "founder_name": person_name or None, "founder_email": email}
