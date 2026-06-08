import logging
import json
from typing import List, Dict
from urllib.parse import urljoin

from src.http_client import safe_get

log = logging.getLogger(__name__)

BASE_URL = "https://wellfound.com"


def scrape(cfg) -> List[Dict[str, str]]:
    log.info("Wellfound blocks automated scraping (403). Skipping.")
    return []
