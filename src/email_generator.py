import logging
import re
from typing import List, Dict

log = logging.getLogger(__name__)


def generate_emails(startups: List[Dict]) -> List[Dict]:
    results = []
    for s in startups:
        email = _generate_single(s)
        results.append({**s, "draft_email": email})
    return results


def _short_name(raw: str) -> str:
    raw = re.sub(r"[-–—|:].*$", "", raw).strip()
    raw = raw.split(",")[0].strip()
    words = raw.split()
    if len(words) <= 3:
        return raw
    return " ".join(words[:3])


def _clean_desc(raw: str) -> str:
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = re.sub(r"\s*\|\s*(Discussion|Product Hunt.*|)$", "", raw, flags=re.I).strip()
    raw = raw.split(".")[0].strip()
    return raw[:100]


def _generate_single(startup: Dict) -> str:
    founder = startup.get("founder_name")
    name = startup.get("name", "")
    need = startup.get("critical_need") or ""
    desc = startup.get("description", "") or ""

    if founder:
        first_name = founder.split()[0]
    else:
        short = _short_name(name) if name else "there"
        first_name = short

    hook = need.lower().rstrip(".")
    if not hook and desc:
        hook = _clean_desc(desc).lower().rstrip(".")
    if not hook:
        hook = "saw your startup and think I could help"

    body = (
        f"Hi {first_name},\n\n"
        f"{hook}.\n\n"
        f"I build dashboards, automate workflows, and create AI tools for early-stage startups. "
        f"Want to hop on a quick call to see if I can help?"
    )

    return body
