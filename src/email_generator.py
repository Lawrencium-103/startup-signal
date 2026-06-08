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
    founder = startup.get("founder_name") or "there"
    name = startup.get("name", "your startup")
    need = startup.get("critical_need") or "scale operations"
    reason = startup.get("match_reason") or ""
    first_name = founder.split()[0] if founder and founder != "there" else "there"

    if reason:
        body = (
            f"Hi {first_name},\n\n"
            f"I've been following {name} and noticed you're likely focused on {need.lower()}. "
            f"{reason.capitalize()}. "
            f"I'm a data associate who helps early-stage startups build dashboards, automate workflows, "
            f"and set up AI tools to make faster, data-driven decisions. "
            f"Would you be open to a 15-min chat this week about how I could help?"
        )
    else:
        body = (
            f"Hi {first_name},\n\n"
            f"I've been following {name} and think I could help with {need.lower()}. "
            f"I build dashboards (Tableau, Power BI), automate workflows (n8n, GitHub Actions), "
            f"and create internal AI tools. "
            f"Would you be open to a 15-min chat this week?"
        )

    return body
