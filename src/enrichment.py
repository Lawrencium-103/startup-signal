import logging
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
            time.sleep(0.5)

    log.info(f"Enriched {sum(1 for e in enriched if e.get('founder_name'))}/{len(enriched)} startups")
    return enriched


def enrich_single(startup: Dict[str, str], cfg) -> Dict[str, Optional[str]]:
    domain = urlparse(startup.get("url", "")).netloc or ""
    if not domain:
        return {**startup, "founder_name": None, "founder_email": None}

    try:
        resp = requests.post(
            "https://api.apollo.io/v1/people/match",
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "X-Api-Key": cfg.apollo_api_key,
            },
            json={
                "domain": domain,
                "reveal_personal_emails": True,
                "reveal_phone": False,
            },
            timeout=30,
        )
        data = resp.json()
    except Exception as e:
        log.debug(f"Apollo API error for {domain}: {e}")
        return {**startup, "founder_name": None, "founder_email": None}

    person = data.get("person") or data.get("people", [{}])[0] if data.get("people") else None
    if not person:
        return {**startup, "founder_name": None, "founder_email": None}

    name = person.get("name") or person.get("first_name", "") + " " + person.get("last_name", "")
    name = name.strip() or None
    email = person.get("email") or person.get("personal_email") or None

    return {
        **startup,
        "founder_name": name,
        "founder_email": email,
    }
