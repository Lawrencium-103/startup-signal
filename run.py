#!/usr/bin/env python3
import logging
import sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("signal")


def main():
    from src.config import Config
    from src.scrapers import run_all_scrapers
    from src.analyzer import analyze_startups
    from src.enrichment import enrich_startups
    from src.email_generator import generate_emails
    from src.reporter import send_report, build_html_report
    from pathlib import Path

    cfg = Config.from_env()
    log.info("=" * 50)
    log.info("Startup Signal — Daily Discovery Engine")
    log.info("=" * 50)

    all_startups = run_all_scrapers(cfg)
    if not all_startups:
        log.warning("No startups discovered. Exiting.")
        return

    scored = analyze_startups(all_startups, cfg)
    top5 = scored[:5]
    log.info(f"Top 5 matches:")
    for i, s in enumerate(top5, 1):
        log.info(f"  {i}. {s.get('name')} (score={s.get('match_score',0)})")

    enriched = enrich_startups(top5, cfg)
    finalized = generate_emails(enriched)

    from src.history import merge_and_save
    merge_and_save(all_startups, "reports/startups.csv")

    html = build_html_report(finalized, all_startups)
    out_dir = Path("reports")
    out_dir.mkdir(exist_ok=True)
    report_path = out_dir / "index.html"
    report_path.write_text(html, encoding="utf-8")
    log.info(f"Report saved to {report_path}")

    from datetime import date
    dated_path = out_dir / f"report-{date.today().isoformat()}.html"
    dated_path.write_text(html, encoding="utf-8")

    send_report(finalized, cfg, all_startups)

    log.info("Done. Happy hunting!")


if __name__ == "__main__":
    main()
