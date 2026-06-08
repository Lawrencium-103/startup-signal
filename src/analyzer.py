import logging
import time
import re
from typing import List, Dict

log = logging.getLogger(__name__)

SKILL_PROFILE = """
I am a data associate with expertise in:
- Dashboards: Tableau, Power BI, Google Data Studio, Looker
- Automation: n8n, GitHub Actions, cron jobs, ClickUp, project management workflows
- AI/ML: Python, LangGraph, Langflow, building internal agentic AI tools
- Data: SQL, R, data aggregation, database design & maintenance, data pipelines
- Analytics: Marketing analytics, forecasting, cohort analysis, A/B testing, evaluation
- Web: Next.js, Leaflet, Google Sheets/AppScript
- Content: Automated content workflows, image generation, video generation workflows
- Other: Data entry automation, business process automation, CRM integration
"""

KEYWORD_SCORE = {
    "data": 3, "analytics": 3, "dashboard": 5, "tableau": 5, "power bi": 5,
    "looker": 4, "google data studio": 4, "metric": 3, "kpi": 3,
    "automation": 4, "workflow": 3, "n8n": 5, "pipeline": 3,
    "ai": 3, "agent": 4, "llm": 4, "langchain": 4, "langgraph": 5, "langflow": 5,
    "machine learning": 4, "ml": 3, "python": 3, "database": 3, "sql": 3,
    "forecast": 4, "cohort": 4, "marketing analytics": 5, "attribution": 4,
    "crm": 2, "integration": 2, "process": 2, "efficiency": 2,
    "internal tool": 4, "no-code": 2, "low-code": 2,
    "content": 1, "image generation": 2, "video": 1, "seo": 2,
    "b2b": 2, "saas": 1, "enterprise": 2, "startup": 1,
    "growth": 2, "revenue": 2, "conversion": 3, "retention": 3,
    "customer": 1, "user": 1, "product": 1,
}

def keyword_score(description: str) -> int:
    desc = description.lower()
    score = 0
    for keyword, points in KEYWORD_SCORE.items():
        if keyword in desc:
            score += points
    return score

MATCH_PROMPT = """You are a matchmaking analyst. Given a startup and my skill profile, rate how well I can help them.

My Skills:
{skills}

Startup: {name}
Description: {description}
Website: {url}

Respond with ONLY a JSON object:
{{
  "score": <0-100 integer>,
  "reason": "<one sentence why I'm a good fit, mentioning specific skill>",
  "critical_need": "<one sentence about what they critically need that matches my skills>"
}}"""

def _build_match_prompt(startup: Dict) -> str:
    return MATCH_PROMPT.format(
        skills=SKILL_PROFILE.strip(),
        name=startup.get("name", "Unknown"),
        description=startup.get("description", ""),
        url=startup.get("url", ""),
    )

def analyze_startups(startups: List[Dict], cfg) -> List[Dict]:
    if not cfg.groq_api_key and not cfg.nvidia_api_key and not cfg.openai_api_key:
        log.warning("No AI API key configured, using keyword scoring only")
        for s in startups:
            s["match_score"] = keyword_score(s.get("description", ""))
            s["match_reason"] = "keyword match"
            s["critical_need"] = ""
        return sorted(startups, key=lambda x: x.get("match_score", 0), reverse=True)

    for s in startups:
        s["match_score"] = keyword_score(s.get("description", ""))

    ranked = sorted(startups, key=lambda x: x.get("match_score", 0), reverse=True)
    log.info(f"Keyword-scored {len(ranked)} startups")

    candidates = ranked[:20]
    log.info(f"AI-analyzing top {len(candidates)} candidates for skill match")

    results = []
    consecutive_fail = 0
    for i, s in enumerate(candidates):
        if i > 0 and consecutive_fail < 2:
            time.sleep(3)
        result = _analyze_match(s, cfg)
        if result.get("match_score", 0) > 0:
            consecutive_fail = 0
        else:
            consecutive_fail += 1
        results.append(result)
        if consecutive_fail >= 2:
            log.warning("Persistent AI failures. Using keyword scores for remaining.")
            for rem in candidates[i + 1:]:
                results.append(rem)
            break

    for rem in ranked[20:]:
        results.append(rem)

    results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    for r in results:
        log.info(f"  {r.get('name','?')}: score={r.get('match_score',0)} — {r.get('match_reason','')[:60]}")
    return results

def _analyze_match(startup: Dict, cfg) -> Dict:
    prompt = _build_match_prompt(startup)
    raw = ""
    if cfg.groq_api_key:
        raw = _call_groq(prompt, cfg)
    elif cfg.nvidia_api_key:
        raw = _call_nvidia(prompt, cfg)
    elif cfg.openai_api_key:
        raw = _call_openai(prompt, cfg)

    score = 0
    reason = ""
    need = ""

    if raw.strip().startswith("{"):
        try:
            import json
            data = json.loads(raw)
            score = int(data.get("score", 0))
            reason = data.get("reason", "")
            need = data.get("critical_need", "")
        except Exception:
            log.debug(f"Failed to parse AI response: {raw[:100]}")
            score = keyword_score(startup.get("description", ""))

    if score <= 0:
        score = keyword_score(startup.get("description", ""))
        reason = "keyword match (AI parse failed)"

    return {**startup, "match_score": score, "match_reason": reason, "critical_need": need}


def _call_openai(prompt: str, cfg) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=cfg.openai_api_key)
    try:
        resp = client.chat.completions.create(
            model=cfg.ai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.warning(f"OpenAI API error: {e}")
        return ""


def _call_groq(prompt: str, cfg) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=cfg.groq_api_key, base_url="https://api.groq.com/openai/v1")
    try:
        resp = client.chat.completions.create(
            model=cfg.groq_model or "llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        log.warning(f"Groq API error: {e}")
        return ""


def _call_nvidia(prompt: str, cfg) -> str:
    import requests as _req
    import json
    import time as _time
    for attempt in range(3):
        try:
            resp = _req.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {cfg.nvidia_api_key}", "Content-Type": "application/json"},
                json={
                    "model": cfg.nvidia_model or "meta/llama-3.3-70b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 200,
                },
                timeout=30,
            )
            if resp.status_code == 429:
                _time.sleep(3 ** attempt)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if "429" in str(e):
                _time.sleep(3 ** attempt)
                continue
            log.warning(f"NVIDIA API error: {e}")
            return ""
    return ""
