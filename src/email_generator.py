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

    first_name = founder.split()[0] if founder and founder != "there" else "there"

    body = (
        f"Hi {first_name},\n\n"
        f"I've been following {name} and noticed you likely {need.lower()}. "
        f"I'm a freelance data/revops specialist who helps early-stage startups "
        f"set up the data infrastructure they need to make faster, smarter decisions. "
        f"Would you be open to a 15-min chat this week about how I could help you "
        f"get this in place?"
    )

    return body
