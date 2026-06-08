import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict

log = logging.getLogger(__name__)


def build_html_report(startups: List[Dict]) -> str:
    rows = ""
    for i, s in enumerate(startups, 1):
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

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:900px;margin:0 auto;padding:20px;">
    <h1 style="color:#111;">Startup Signal</h1>
    <p style="color:#666;">Top {len(startups)} matches for your skills today</p>
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
    <p style="color:#999;font-size:12px;margin-top:20px;">
        Startup Signal — Review each email before sending. No automated outreach.
    </p>
</body>
</html>"""
    return html


def send_report(startups: List[Dict], cfg) -> bool:
    if not startups:
        log.info("No startups to report")
        return False

    html = build_html_report(startups)

    if not cfg.email_to or not cfg.smtp_password:
        log.warning("Email not configured. Top matches:")
        for s in startups:
            log.info(f"  {s.get('name')} (score={s.get('match_score',0)}): {s.get('critical_need','')}")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = cfg.email_from
    msg["To"] = cfg.email_to
    msg["Subject"] = f"Startup Signal — Top {len(startups)} matches today"

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
