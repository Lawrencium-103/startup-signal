import logging
import re
from typing import List, Dict
from xml.etree import ElementTree

from src.http_client import safe_get

log = logging.getLogger(__name__)

STARTUP_KEYWORDS = [
    "launch", "startup", "funding", "seed", "series a", "series b",
    "raises", "acquired", "debuts", "introduces", "unveils",
    "beta", "exits stealth", "ipo",
]


def scrape(cfg) -> List[Dict[str, str]]:
    resp = safe_get("https://techcrunch.com/feed/", min_delay=3.0, max_delay=5.0)
    if resp is None:
        return []

    try:
        root = ElementTree.fromstring(resp.content)
    except ElementTree.ParseError:
        return []

    startups = []
    for item in root.findall(".//item"):
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        desc_el = item.find("description")
        desc = ""
        if desc_el is not None and desc_el.text:
            desc = re.sub(r"<[^>]+>", "", desc_el.text).strip()[:300]

        if not title or len(title) < 5:
            continue
        if not any(kw in title.lower() for kw in STARTUP_KEYWORDS):
            continue

        name = re.split(
            r"\s+(?:raises|launches|debuts|introduces|unveils|acquires|gets|scores|lands|picks up)",
            title, flags=re.I,
        )[0].strip()
        name = re.sub(r"\s+&\s+.*", "", name).strip()
        if len(name) < 2:
            name = title[:60]
        if not desc:
            desc = title[:300]

        startups.append({"name": name, "description": desc[:300], "url": link})

    return startups[:15]
