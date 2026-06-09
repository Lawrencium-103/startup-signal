import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict

log = logging.getLogger(__name__)


def build_html_report(top_startups: List[Dict], all_startups: List[Dict] = None) -> str:
    rows = ""
    for i, s in enumerate(top_startups, 1):
        name = s.get("name", "Unknown")
        founder = s.get("founder_name") or "Not found"
        email = s.get("founder_email") or "Not found"
        need = s.get("critical_need") or "Not analyzed"
        draft = s.get("draft_email", "")
        desc = s.get("description", "") or ""
        score = s.get("match_score", 0)
        reason = s.get("match_reason", "")

        rows += f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #eee;">{i}</td>
            <td style="padding:10px;border-bottom:1px solid #eee;">
                <strong>{name}</strong><br>
                <small style="color:#666;">{desc[:120]}</small>
            </td>
            <td style="padding:10px;border-bottom:1px solid #eee;">
                <span style="font-weight:bold;color:{"#22c55e" if score >= 70 else "#eab308" if score >= 40 else "#ef4444"};">{score}%</span><br>
                <small style="color:#555;">{reason[:80]}</small>
            </td>
            <td style="padding:10px;border-bottom:1px solid #eee;">
                {founder}<br>
                <small style="color:#666;">{email}</small>
            </td>
            <td style="padding:10px;border-bottom:1px solid #eee;">
                <pre style="white-space:pre-wrap;font-size:12px;background:#f9f9f9;padding:8px;border-radius:4px;max-width:350px;">{draft}</pre>
            </td>
        </tr>"""

    all_rows = ""
    if all_startups:
        for s in all_startups:
            n = s.get("name", "")
            u = (s.get("url") or "").strip()
            src = s.get("source", "")
            dt = s.get("extracted_at", "")
            desc_short = (s.get("description") or "")[:100]
            link = f'<a href="{u}" target="_blank">{u}</a>' if u else "—"
            all_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;font-size:13px;">{n}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;font-size:13px;">{link}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;font-size:13px;color:#666;">{desc_short}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;font-size:13px;color:#666;">{src}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;font-size:13px;color:#666;">{dt}</td>
        </tr>"""

    all_section = ""
    if all_startups and all_rows:
        count = len(all_startups)
        all_section = f"""
    <h2 style="color:#111;margin-top:40px;">All Startups ({count})</h2>
    <p style="color:#666;">Full dataset from all scrapers. <a href="startups.csv">Download CSV</a></p>
    <div style="max-height:500px;overflow-y:auto;border:1px solid #ddd;border-radius:4px;">
    <table style="width:100%;border-collapse:collapse;">
        <thead>
            <tr style="background:#f5f5f5;position:sticky;top:0;">
                <th style="padding:8px;text-align:left;border-bottom:2px solid #ddd;font-size:13px;">Name</th>
                <th style="padding:8px;text-align:left;border-bottom:2px solid #ddd;font-size:13px;">URL</th>
                <th style="padding:8px;text-align:left;border-bottom:2px solid #ddd;font-size:13px;">Description</th>
                <th style="padding:8px;text-align:left;border-bottom:2px solid #ddd;font-size:13px;">Source</th>
                <th style="padding:8px;text-align:left;border-bottom:2px solid #ddd;font-size:13px;">Date</th>
            </tr>
        </thead>
        <tbody>{all_rows}</tbody>
    </table>
    </div>"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:960px;margin:0 auto;padding:20px;">
    <h1 style="color:#111;">Startup Signal</h1>
    <p style="color:#999;font-size:14px;">{date.today().isoformat()}</p>
    <p style="color:#666;">Top {len(top_startups)} matches for your skills today</p>
    <table style="width:100%;border-collapse:collapse;margin-top:16px;">
        <thead>
            <tr style="background:#f5f5f5;">
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ddd;">#</th>
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ddd;">Company</th>
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ddd;">Match</th>
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ddd;">Founder</th>
                <th style="padding:10px;text-align:left;border-bottom:2px solid #ddd;">Draft Email</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    {all_section}
    <p style="color:#999;font-size:12px;margin-top:20px;">
        Startup Signal — Review each email before sending. No automated outreach.
    </p>
</body>
</html>"""
    return html


def send_report(startups: List[Dict], cfg, all_startups: List[Dict] = None) -> bool:
    if not startups:
        log.info("No startups to report")
        return False

    html = build_html_report(startups, all_startups)

    if not cfg.email_to or not cfg.smtp_password:
        log.warning("Email not configured. Top matches:")
        for s in startups:
            log.info(f"  {s.get('name')} (score={s.get('match_score',0)}): {s.get('critical_need','')}")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = cfg.email_from
    msg["To"] = cfg.email_to
    msg["Subject"] = f"Startup Signal — {date.today().isoformat()} — Top {len(startups)} matches"

    msg.attach(MIMEText(f"Startup Signal found {len(startups)} top matches today. Open in HTML for full report.", "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port)
        server.starttls()
        server.login(cfg.smtp_username, cfg.smtp_password)
        server.sendmail(cfg.email_from, cfg.email_to, msg.as_string())
        server.quit()
        log.info(f"Report sent to {cfg.email_to}")
        return True
    except Exception as e:
        log.error(f"Failed to send email: {e}")
        return False
