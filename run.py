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
    from src.enrichment import enrich_startups
    from src.analyzer import analyze_startups
    from src.email_generator import generate_emails
    from src.reporter import send_report, build_html_report
    from pathlib import Path

    cfg = Config.from_env()
    log.info("=" * 50)
    log.info("Startup Signal — Daily Discovery Engine")
    log.info("=" * 50)

    startups = run_all_scrapers(cfg)
    if not startups:
        log.warning("No startups discovered. Exiting.")
        return

    enriched = enrich_startups(startups, cfg)
    analyzed = analyze_startups(enriched, cfg)
    emails = generate_emails(analyzed)

    # Save HTML report locally for artifact / Pages upload
    html = build_html_report(emails)
    out_dir = Path("reports")
    out_dir.mkdir(exist_ok=True)
    report_path = out_dir / "latest.html"
    report_path.write_text(html, encoding="utf-8")
    log.info(f"Report saved to {report_path}")

    # Also save a timestamped copy
    from datetime import date
    dated_path = out_dir / f"report-{date.today().isoformat()}.html"
    dated_path.write_text(html, encoding="utf-8")

    send_report(emails, cfg)

    log.info("Done. Happy hunting!")


if __name__ == "__main__":
    main()
