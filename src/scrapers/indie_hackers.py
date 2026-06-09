import logging
import requests
from xml.etree import ElementTree
from typing import List, Dict

log = logging.getLogger(__name__)


def scrape(cfg) -> List[Dict[str, str]]:
    try:
        resp = requests.get(
            "https://www.indiehackers.com/rss.xml",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        if resp.status_code != 200:
            log.info(f"Indie Hackers RSS: {resp.status_code}")
            return []
        root = ElementTree.fromstring(resp.content)
        startups = []
        for item in root.iter("{http://www.w3.org/2005/Atom}entry"):
            title = ""
            link = ""
            desc = ""
            for child in item:
                tag = child.tag.split("}")[-1]
                if tag == "title":
                    title = (child.text or "").strip()
                elif tag == "link":
                    link = child.attrib.get("href", "")
                elif tag == "content":
                    desc = (child.text or "")[:200]
            if title:
                startups.append({"name": title[:100], "description": desc, "url": link})
        log.info(f"Indie Hackers: {len(startups)} entries")
        return startups
    except Exception as e:
        log.info(f"Indie Hackers scrape error: {e}")
        return []
