import logging
import re
import time
import random
from datetime import date
from typing import List, Dict
from urllib.parse import urlparse

log = logging.getLogger(__name__)

SCRAPERS = [
    ("YC Launches", "src.scrapers.yc_launches"),
    ("Product Hunt", "src.scrapers.product_hunt"),
    ("BetaList", "src.scrapers.betalist"),
    ("TechCrunch", "src.scrapers.techcrunch"),
    ("a16z Portfolio", "src.scrapers.a16z_portfolio"),
    ("Wellfound", "src.scrapers.wellfound"),
    ("Reddit r/startups", "src.scrapers.reddit_startups"),
    ("Crunchbase", "src.scrapers.crunchbase"),
    ("Startup Gallery", "src.scrapers.startup_gallery"),
]

TODAY = date.today().isoformat()


def import_scraper(path: str):
    import importlib
    mod = importlib.import_module(path)
    return mod.scrape


def deduplicate(startups: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    unique = []
    for s in startups:
        url = s.get("url", "")
        name = s.get("name", "")
        if not url and not name:
            continue
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") if parsed.path else ""
        key = f"{parsed.netloc}{path}" if parsed.netloc else name.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def clean(startups: List[Dict[str, str]]) -> List[Dict[str, str]]:
    cleaned = []
    for s in startups:
        name = s.get("name", "")
        if len(name) < 2:
            continue
        if len(name) > 100:
            continue
        if re.search(r"[\u4e00-\u9fff\u0400-\u04ff]", name):
            continue
        cleaned.append(s)
    return cleaned


def run_all_scrapers(cfg) -> List[Dict[str, str]]:
    all_startups = []

    for name, module_path in SCRAPERS:
        gap = random.uniform(3.0, 6.0)
        log.info(f"Waiting {gap:.1f}s before scraping {name}...")
        time.sleep(gap)

        try:
            scraper_fn = import_scraper(module_path)
            results = scraper_fn(cfg)
            for s in results:
                s["source"] = name
                s["extracted_at"] = TODAY
            log.info(f"{name}: found {len(results)} startups")
            all_startups.extend(results)
        except Exception as e:
            log.warning(f"{name} scraper failed: {e}")

    unique = deduplicate(all_startups)
    cleaned = clean(unique)
    log.info(f"Total unique startups: {len(cleaned)} (from {len(all_startups)} raw)")
    return cleaned
