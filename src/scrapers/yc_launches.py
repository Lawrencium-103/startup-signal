import logging
import requests
from typing import List, Dict

log = logging.getLogger(__name__)


def scrape(cfg) -> List[Dict[str, str]]:
    startups = []
    for page in range(1, 4):
        try:
            resp = requests.get(
                "https://www.ycombinator.com/api/v1/companies",
                params={"page": page},
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=15,
            )
            if resp.status_code != 200:
                log.info(f"YC API page {page}: {resp.status_code}")
                break
            data = resp.json()
            companies = data.get("companies", [])
            if not companies:
                break
            for c in companies:
                name = c.get("name", "")
                if not name:
                    continue
                startups.append({
                    "name": name,
                    "description": c.get("one_liner", "") or "",
                    "url": c.get("url", "") or f"https://www.ycombinator.com/companies/{c.get('slug','')}",
                })
            log.info(f"YC API page {page}: {len(companies)} companies")
        except Exception as e:
            log.info(f"YC API page {page}: {e}")
            break

    return startups
