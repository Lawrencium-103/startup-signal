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
    reason = startup.get("match_reason") or ""
    first_name = founder.split()[0] if founder else "there"

    if need and reason:
        body = (
            f"Hi {first_name},\n\n"
            f"Saw {name} — {need.lower().rstrip('.')}.\n\n"
            f"That's exactly what I do. I build dashboards, automate workflows, and set up AI tools "
            f"for early-stage startups. "
            f"Would you be open to a quick call this week?"
        )
    else:
        body = (
            f"Hi {first_name},\n\n"
            f"Saw {name} and think I could help. I build dashboards (Tableau, Power BI), "
            f"automate workflows (n8n), and create internal AI tools for startups.\n\n"
            f"Open to a quick chat?"
        )

    return body
