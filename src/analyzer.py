import logging
import time
from typing import List, Dict

log = logging.getLogger(__name__)

MAX_ANALYZE = 10


def analyze_startups(startups: List[Dict], cfg) -> List[Dict]:
    if not cfg.openai_api_key and not cfg.groq_api_key and not cfg.nvidia_api_key:
        log.warning("No AI API key configured, skipping analysis")
        return [{**s, "critical_need": ""} for s in startups]

    to_analyze = startups[:MAX_ANALYZE]
    log.info(f"Analyzing {len(to_analyze)}/{len(startups)} startups via {cfg.ai_provider}")

    results = []
    consecutive_ratelimit = 0
    for i, s in enumerate(to_analyze):
        if i > 0 and consecutive_ratelimit < 2:
            wait = 3
            log.info(f"Waiting {wait}s before next analysis...")
            time.sleep(wait)
        result = analyze_single(s, cfg)
        if not result.get("critical_need"):
            consecutive_ratelimit += 1
        else:
            consecutive_ratelimit = 0
        results.append(result)
        if consecutive_ratelimit >= 2:
            log.warning("Persistent rate limiting detected. Skipping remaining analysis.")
            for remaining in to_analyze[i + 1:]:
                results.append({**remaining, "critical_need": ""})
            break

    for s in startups[MAX_ANALYZE:]:
        results.append({**s, "critical_need": ""})

    return results


def _build_prompt(startup: Dict) -> str:
    name = startup.get("name", "this startup")
    desc = startup.get("description", "")
    url = startup.get("url", "")
    return (
        f"You are a business analyst. Analyze this startup and identify ONE critical "
        f"business need they must solve right now:\n\n"
        f"Startup: {name}\nDescription: {desc}\nWebsite: {url}\n\n"
        f"Consider: hiring stage, funding round, go-to-market, data infrastructure, "
        f"revenue operations, product-market fit.\n\n"
        f"Respond with a single sentence describing what they critically need next "
        f"(e.g., 'Needs to build their first sales data pipeline to track conversion "
        f"metrics for seed round reporting'). Be specific. Max 25 words."
    )


def analyze_single(startup: Dict, cfg) -> Dict:
    prompt = _build_prompt(startup)
    critical_need = ""

    if cfg.ai_provider == "groq" and cfg.groq_api_key:
        critical_need = _call_groq(prompt, cfg)
    elif cfg.ai_provider == "nvidia" and cfg.nvidia_api_key:
        critical_need = _call_nvidia(prompt, cfg)
    elif cfg.openai_api_key:
        critical_need = _call_openai(prompt, cfg)

    return {**startup, "critical_need": critical_need}


def _call_openai(prompt: str, cfg) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=cfg.openai_api_key)
    try:
        resp = client.chat.completions.create(
            model=cfg.ai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100,
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
            model=cfg.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100,
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
                headers={
                    "Authorization": f"Bearer {cfg.nvidia_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": cfg.nvidia_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 100,
                },
                timeout=30,
            )
            if resp.status_code == 429:
                wait = 3 ** attempt
                log.info(f"NVIDIA rate limited, waiting {wait}s (attempt {attempt+1}/3)")
                _time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                wait = 3 ** attempt
                log.info(f"NVIDIA rate limited, waiting {wait}s (attempt {attempt+1}/3)")
                _time.sleep(wait)
                continue
            log.warning(f"NVIDIA API error: {e}")
            return ""
    log.warning("NVIDIA API rate limit exceeded after 3 retries")
    return ""
