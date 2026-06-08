import logging
from typing import List, Dict

from src.http_client import safe_get

log = logging.getLogger(__name__)


def scrape(cfg) -> List[Dict[str, str]]:
    log.info("Reddit blocks automated scraping without OAuth. Skipping.")
    return []
