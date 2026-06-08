import logging
from typing import List, Dict

log = logging.getLogger(__name__)


def generate_emails(startups: List[Dict]) -> List[Dict]:
    results = []
    for s in startups:
        email = _generate_single(s)
        results.append({**s, "draft_email": email})
    return results


def _generate_single(startup: Dict) -> str:
    founder = startup.get("founder_name")
    name = startup.get("name", "your startup")
    need = startup.get("critical_need") or ""
    desc = startup.get("description", "") or ""

    if founder:
        first_name = founder.split()[0]
    else:
        first_name = name

    # Build a specific hook from the description
    hook = need.lower().rstrip(".")
    if not hook and desc:
        hook = desc[:80].lower().rstrip(".")

    body = (
        f"Hi {first_name},\n\n"
        f"Saw {name} — {hook}.\n\n"
        f"I build dashboards, automate workflows, and create AI tools for early-stage startups. "
        f"Want to hop on a quick call to see if I can help?"
    )

    return body
