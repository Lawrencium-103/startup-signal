import logging
from typing import List, Dict

from src.http_client import safe_get

log = logging.getLogger(__name__)


def scrape(cfg) -> List[Dict[str, str]]:
    log.info("Startup Gallery is JS-rendered with anti-bot protection. Skipping.")
    return []
