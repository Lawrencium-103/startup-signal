import logging
import json
import re
from typing import List, Dict

from src.http_client import safe_get

log = logging.getLogger(__name__)


def scrape(cfg) -> List[Dict[str, str]]:
    resp = safe_get("https://a16z.com/portfolio/", min_delay=3.0, max_delay=5.0)
    if resp is None:
        return []

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "lxml")
    startups = []
    seen = set()

    script = soup.find("script", id=re.compile(r"__NEXT_DATA__", re.I))
    if script:
        try:
            data = json.loads(script.string)
            companies = data.get("props", {}).get("pageProps", {}).get("companies", []) or data.get("props", {}).get("pageProps", {}).get("portfolio", [])
            for c in companies:
                name = c.get("name", "") or c.get("title", "")
                if name and name not in seen:
                    seen.add(name.lower())
                    startups.append({
                        "name": name,
                        "description": c.get("description", "") or c.get("one_liner", "") or "",
                        "url": c.get("url", "") or c.get("website", "") or c.get("link", "") or "",
                    })
            if startups:
                return startups
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    for link in soup.select("a[href^='http']"):
        href = link["href"]
        text = link.get_text(strip=True)
        if not text or len(text) < 3:
            continue
        domain = re.match(r"https?://([^/]+)", href)
        if not domain:
            continue
        domain = domain.group(1)
        if domain in seen:
            continue
        if any(ignore in domain for ignore in [
            "a16z.com", "github.com", "twitter.com", "linkedin.com",
            "youtube.com", "facebook.com", "instagram.com", "crunchbase.com",
        ]):
            continue
        if any(ignore in text.lower() for ignore in ["portfolio", "companies", "investments", "a16z"]):
            continue
        seen.add(domain)
        parent = link.find_parent(["div", "li", "article", "section"])
        desc = ""
        if parent:
            for p in parent.select("p, [class*='desc'], [class*='summary']"):
                t = p.get_text(strip=True)
                if t and len(t) > 10 and t.lower() != text.lower():
                    desc = t
                    break
        startups.append({"name": text, "description": desc[:300], "url": href})

    return startups
