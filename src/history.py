import logging
import csv
import io
import os
import requests
import zipfile
from datetime import date
from typing import List, Dict

log = logging.getLogger(__name__)


def _gh_headers():
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json"}
    return {}


def _download_previous_csv():
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        return {}
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/actions/artifacts?name=startup-signal-report&per_page=1",
            headers=_gh_headers(), timeout=15,
        )
        if not resp.ok or not resp.json().get("artifacts"):
            return {}
        aid = resp.json()["artifacts"][0]["id"]
        dl = requests.get(
            f"https://api.github.com/repos/{repo}/actions/artifacts/{aid}/zip",
            headers=_gh_headers(), timeout=30,
        )
        if not dl.ok:
            return {}
        z = zipfile.ZipFile(io.BytesIO(dl.content))
        if "startups.csv" not in z.namelist():
            return {}
        reader = csv.DictReader(io.StringIO(z.read("startups.csv").decode("utf-8")))
        seen = {}
        for row in reader:
            url = (row.get("url") or "").strip()
            if url:
                seen[url] = row
        log.info(f"Loaded {len(seen)} historical startups from previous artifact")
        return seen
    except Exception as e:
        log.debug(f"History download: {e}")
        return {}


def merge_and_save(all_startups: List[Dict], csv_path: str):
    today = date.today().isoformat()
    previous = _download_previous_csv()
    seen_urls = set(previous.keys())

    new_rows = 0
    for s in all_startups:
        url = (s.get("url") or "").strip()
        if url and url not in seen_urls:
            previous[url] = {
                "name": s.get("name", ""),
                "url": url,
                "description": (s.get("description", "") or "")[:200],
                "source": s.get("source", ""),
                "extracted_at": s.get("extracted_at", today),
            }
            seen_urls.add(url)
            new_rows += 1

    if new_rows == 0:
        log.info("No new startups to add to history")
    else:
        log.info(f"Added {new_rows} new startups to history ({len(previous)} total)")

    fieldnames = ["name", "url", "description", "source", "extracted_at"]
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(previous.values(), key=lambda x: x.get("extracted_at", ""), reverse=True))
    log.info(f"History saved to {csv_path} ({len(previous)} startups)")
