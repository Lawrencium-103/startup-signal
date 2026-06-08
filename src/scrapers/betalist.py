import logging
import re
from typing import List, Dict
from xml.etree import ElementTree

from src.http_client import safe_get

log = logging.getLogger(__name__)

ATOM_NS = "http://www.w3.org/2005/Atom"
NS = {"atom": ATOM_NS}


def scrape(cfg) -> List[Dict[str, str]]:
    resp = safe_get("https://feeds.feedburner.com/BetaList", min_delay=3.0, max_delay=5.0)
    if resp is None:
        return []

    try:
        root = ElementTree.fromstring(resp.content)
    except ElementTree.ParseError:
        return []

    startups = []
    for entry in root.findall(".//atom:entry", NS):
        title_el = entry.find("atom:title", NS)
        link_el = entry.find("atom:link", NS)
        content_el = entry.find("atom:content", NS)

        name = title_el.text.strip() if title_el is not None and title_el.text else ""
        url = link_el.get("href", "") if link_el is not None else ""
        desc = ""
        if content_el is not None and content_el.text:
            desc = re.sub(r"<[^>]+>", "", content_el.text).strip()[:300]

        if name and len(name) > 2:
            startups.append({"name": name, "description": desc, "url": url})

    return startups
