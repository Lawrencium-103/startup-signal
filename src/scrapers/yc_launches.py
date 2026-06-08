import logging
import json
import re
from typing import List, Dict

from src.http_client import safe_get

log = logging.getLogger(__name__)


def scrape(cfg) -> List[Dict[str, str]]:
    resp = safe_get("https://www.ycombinator.com/companies/", min_delay=3.0, max_delay=5.0)
    if resp is None:
        return []

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "lxml")

    script = soup.find("script", id=re.compile(r"__NEXT_DATA__", re.I))
    if script:
        try:
            data = json.loads(script.string)
            companies = data.get("props", {}).get("pageProps", {}).get("companies", [])
            return [
                {
                    "name": c.get("name", ""),
                    "description": c.get("one_liner", "") or c.get("description", "") or "",
                    "url": c.get("url", "") or c.get("company_url", "")
                    or (f"https://www.ycombinator.com/companies/{c['slug']}" if c.get("slug") else ""),
                }
                for c in companies if c.get("name")
            ]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.debug(f"YC Next.js data parse failed: {e}")

    startups = []
    for card in soup.select("[class*='company'], [class*='card'], article"):
        name_el = card.select_one("h2, h3, h4, [class*='name'], [class*='title'], strong, a")
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        if not name or len(name) < 2:
            continue
        desc_el = card.select_one("p, [class*='desc'], [class*='tagline']")
        desc = desc_el.get_text(strip=True)[:300] if desc_el else ""
        link = name_el if name_el.name == "a" else card.select_one("a[href]")
        url = ""
        if link and link.get("href"):
            url = link["href"]
            if not url.startswith("http"):
                url = "https://www.ycombinator.com" + url
        startups.append({"name": name, "description": desc, "url": url})

    return startups
