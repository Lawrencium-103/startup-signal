import logging
import requests
from typing import List, Dict

log = logging.getLogger(__name__)


def scrape(cfg) -> List[Dict[str, str]]:
    try:
        resp = requests.get(
            "https://www.reddit.com/r/startups/.json",
            headers={
                "User-Agent": "StartupSignal/1.0 (by /u/startupsignal)",
                "Accept": "application/json",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            log.info(f"Reddit: {resp.status_code}")
            return []
        data = resp.json()
        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            title = post.get("title", "")
            if not title:
                continue
            url = post.get("url", "") or f"https://reddit.com{post.get('permalink','')}"
            selftext = (post.get("selftext", "") or "")[:200]
            posts.append({"name": title[:100], "description": selftext, "url": url})
        log.info(f"Reddit: {len(posts)} posts from r/startups")
        return posts
    except Exception as e:
        log.info(f"Reddit scrape error: {e}")
        return []
