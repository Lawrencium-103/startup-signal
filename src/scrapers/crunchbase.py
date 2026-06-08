import logging
from typing import List, Dict

from src.http_client import safe_get, safe_post

log = logging.getLogger(__name__)


def scrape(cfg) -> List[Dict[str, str]]:
    api_key = cfg.crunchbase_api_key
    if not api_key:
        log.info("Crunchbase API key not configured, skipping")
        return []

    resp = safe_post(
        "https://api.crunchbase.com/api/v4/searches/organizations",
        json_data={
            "field_ids": ["name", "short_description", "website_url", "created_at"],
            "order": [{"field_id": "created_at", "sort": "desc"}],
            "limit": 20,
        },
        params={"user_key": api_key},
        min_delay=2.0,
        max_delay=3.0,
    )
    if resp is None:
        return []

    startups = []
    try:
        data = resp.json()
        for entity in data.get("entities", []):
            props = entity.get("properties", {})
            name = props.get("name", "")
            desc = props.get("short_description", "") or ""
            website = props.get("website_url", "") or ""
            if name and website:
                startups.append({"name": name, "description": desc, "url": website})
    except Exception as e:
        log.warning(f"Crunchbase response parse failed: {e}")

    return startups
