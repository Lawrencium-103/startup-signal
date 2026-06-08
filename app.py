#!/usr/bin/env python3
import logging
import sys
import traceback
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("app")

import gradio as gr
from src.config import Config
from src.scrapers import run_all_scrapers
from src.enrichment import enrich_startups
from src.analyzer import analyze_startups
from src.email_generator import generate_emails
from src.reporter import build_html_report


def run_signal():
    try:
        cfg = Config.from_env()

        log.info("Discovering startups...")
        startups = run_all_scrapers(cfg)
        if not startups:
            return "<h2>No startups discovered today.</h2><p>All sources returned empty. Try again later.</p>"

        yield f"<h2>Step 1/4: Discovered {len(startups)} startups</h2><p>Enriching with founder data...</p>"

        enriched = enrich_startups(startups, cfg)
        enriched_count = sum(1 for e in enriched if e.get("founder_email"))
        yield f"<h2>Step 2/4: Enriched {enriched_count}/{len(enriched)} founders</h2><p>Running AI analysis...</p>"

        analyzed = analyze_startups(enriched, cfg)
        analyzed_count = sum(1 for a in analyzed if a.get("critical_need"))
        yield f"<h2>Step 3/4: Analyzed {analyzed_count}/{len(analyzed)} startups</h2><p>Generating email drafts...</p>"

        emails = generate_emails(analyzed)
        yield f"<h2>Step 4/4: {len(emails)} email drafts ready</h2><p>Building report...</p>"

        html = build_html_report(emails)
        yield html

    except Exception as e:
        tb = traceback.format_exc()
        yield f"<h2>Error</h2><pre>{tb}</pre>"


with gr.Blocks(
    title="Startup Signal",
    theme=gr.themes.Soft(),
    css="footer {display:none !important}",
) as demo:
    gr.Markdown(
        """
        # Startup Signal
        **Discover new startups, identify decision-makers, and generate cold email drafts.**
        """
    )
    with gr.Row():
        run_btn = gr.Button("Run Discovery", variant="primary", scale=2)
    output = gr.HTML(label="Results")
    run_btn.click(fn=run_signal, outputs=output, queue=True)

    gr.Markdown(
        """
        ---
        **Sources:** Y Combinator Launches, a16z Portfolio, Product Hunt, Wellfound,
        BetaList, Reddit r/startups, Crunchbase

        **Note:** Review each email before sending. No automated outreach.
        """
    )

demo.queue()
demo.launch(server_name="0.0.0.0", server_port=7860)
