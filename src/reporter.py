import json
import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict

log = logging.getLogger(__name__)

SOURCE_COLORS = {
    "YC API": "#f60",
    "Product Hunt": "#da552f",
    "BetaList": "#4285f4",
    "TechCrunch": "#0a9e01",
    "a16z Portfolio": "#000",
    "Reddit r/startups": "#ff4500",
    "Indie Hackers": "#16a34a",
    "Crunchbase": "#0266ff",
}


def _score_color(s):
    return "#22c55e" if s >= 70 else "#eab308" if s >= 40 else "#ef4444"


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _card(s, i):
    name = _esc(s.get("name", "Unknown"))
    desc = _esc((s.get("description") or "")[:150])
    score = s.get("match_score", 0)
    reason = _esc(s.get("match_reason", ""))
    need = _esc(s.get("critical_need", ""))
    founder = _esc(s.get("founder_name") or "")
    founder_email = _esc(s.get("founder_email") or "")
    draft = _esc(s.get("draft_email", ""))
    url = _esc((s.get("url") or "").strip())
    sc = _score_color(score)
    link = f'<a href="{url}" class="card-link" target="_blank">{url}</a>' if url else ""
    f_info = f'<span class="founder">{founder}</span><span class="femail">{founder_email}</span>' if founder else '<span class="founder nf">Not found</span>'
    draft_html = f'<pre class="draft">{draft}</pre>' if draft else ""
    return f"""<div class="mc" data-score="{score}">
  <div class="mc-h">
    <span class="rank">#{i}</span>
    <span class="sc" style="background:{sc}">{score}%</span>
  </div>
  <div class="mc-b">
    <div class="mc-t">
      <h3>{name}</h3>
      <p class="desc">{desc}</p>
      {link}
    </div>
    <div class="mc-m">
      <div class="chip">{reason}</div>
      <div class="need">{need}</div>
    </div>
    <div class="mc-f">
      <div class="fi">{f_info}</div>
      {draft_html}
    </div>
  </div>
</div>"""


def _all_table_row(s):
    name = _esc(s.get("name", ""))
    u = _esc((s.get("url") or "").strip())
    src = _esc(s.get("source", ""))
    dt = _esc(s.get("extracted_at", ""))
    desc = _esc((s.get("description") or "")[:120])
    score = s.get("match_score", -1)
    sc_cls = f'data-score="{score}"' if score >= 0 else ""
    link = f'<a href="{u}" target="_blank" class="alink">{u}</a>' if u else '<span class="no-link">—</span>'
    sc_col = _score_color(score) if score >= 0 else "transparent"
    sc_html = f'<span class="tsc" style="background:{sc_col}">{score}%</span>' if score >= 0 else ""
    color = SOURCE_COLORS.get(src, "#666")
    return f"""<tr {sc_cls}>
  <td class="tn">{name}</td>
  <td class="tu">{link}</td>
  <td class="td">{desc}</td>
  <td class="ts"><span class="src-b" style="background:{color}">{src}</span></td>
  <td class="tt">{dt}</td>
  <td class="tss">{sc_html}</td>
</tr>"""


def build_html_report(top_startups: List[Dict], all_startups: List[Dict] = None) -> str:
    cards = "\n".join(_card(s, i + 1) for i, s in enumerate(top_startups))

    all_rows = ""
    sources = set()
    if all_startups:
        for s in all_startups:
            src = s.get("source", "")
            if src:
                sources.add(src)
            all_rows += _all_table_row(s)

    filter_opts = "".join(f'<option value="{_esc(s)}">{_esc(s)}</option>' for s in sorted(sources))
    today = date.today().isoformat()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Startup Signal — {today}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,sans-serif;background:#f4f5f7;color:#1a1a2e;line-height:1.5}}
.container{{max-width:1040px;margin:0 auto;padding:24px 16px}}
header{{text-align:center;padding:32px 0 24px}}
header h1{{font-size:28px;font-weight:700;letter-spacing:-0.5px}}
header .dt{{color:#888;font-size:14px;margin-top:4px}}
header .sub{{color:#555;font-size:15px;margin-top:8px}}
/* --- filter bar --- */
.fb{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px;align-items:center}}
.fb input,.fb select{{padding:8px 12px;border:1px solid #ddd;border-radius:8px;font-size:14px;background:#fff;flex:1;min-width:160px}}
.fb select{{flex:0 0 auto;min-width:120px}}
.fb .ct{{color:#888;font-size:13px;margin-left:auto}}
/* --- match cards --- */
.mg{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;margin-bottom:40px}}
.mc{{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06);transition:box-shadow .15s}}
.mc:hover{{box-shadow:0 4px 16px rgba(0,0,0,.1)}}
.mc-h{{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:#fafafa;border-bottom:1px solid #f0f0f0}}
.rank{{font-size:13px;color:#999;font-weight:600}}
.sc{{font-size:13px;font-weight:700;color:#fff;padding:3px 10px;border-radius:20px}}
.mc-b{{padding:16px}}
.mc-t h3{{font-size:16px;font-weight:600;margin-bottom:4px}}
.desc{{font-size:13px;color:#666;margin-bottom:6px}}
.card-link{{font-size:12px;color:#2563eb;word-break:break-all}}
.mc-m{{margin:10px 0;display:flex;flex-wrap:wrap;gap:6px}}
.chip{{font-size:11px;background:#f0f0f0;color:#555;padding:3px 8px;border-radius:12px}}
.need{{font-size:12px;color:#2563eb;font-style:italic;width:100%;margin-top:4px}}
.mc-f{{border-top:1px solid #f0f0f0;padding-top:10px;margin-top:8px}}
.fi{{display:flex;gap:8px;align-items:center;font-size:13px}}
.founder{{font-weight:600}}
.founder.nf{{color:#999;font-weight:400}}
.femail{{color:#2563eb}}
.draft{{font-size:12px;background:#f9f9f9;padding:8px;border-radius:6px;margin-top:6px;white-space:pre-wrap;color:#444}}
/* --- all table --- */
.all-s{{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06);margin-top:24px}}
.all-s h2{{font-size:18px;padding:16px 16px 0;font-weight:600}}
.all-s .hint{{font-size:13px;color:#888;padding:4px 16px 12px}}
.tw{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
thead{{background:#fafafa}}
th{{padding:10px 12px;text-align:left;border-bottom:1px solid #eee;font-weight:600;color:#555;white-space:nowrap}}
td{{padding:8px 12px;border-bottom:1px solid #f0f0f0;vertical-align:top}}
.tn{{font-weight:600;white-space:nowrap;max-width:160px;overflow:hidden;text-overflow:ellipsis}}
.alink{{color:#2563eb;word-break:break-all;font-size:12px}}
.no-link{{color:#ccc}}
.td{{color:#666;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.src-b{{display:inline-block;padding:2px 8px;border-radius:10px;color:#fff;font-size:11px;font-weight:600;white-space:nowrap}}
.tt{{color:#999;white-space:nowrap}}
.tsc{{display:inline-block;padding:2px 8px;border-radius:10px;color:#fff;font-size:11px;font-weight:600}}
.tss{{text-align:center}}
.hidden{{display:none!important}}
/* --- footer --- */
footer{{text-align:center;padding:24px 0 40px;font-size:12px;color:#aaa}}
footer a{{color:#888}}
/* --- responsive --- */
@media(max-width:640px){{.mg{{grid-template-columns:1fr}}.fb input,.fb select{{min-width:100%}}}}
</style>
</head>
<body>
<div class="container">
<header>
  <h1>Startup Signal</h1>
  <p class="dt">{today}</p>
  <p class="sub">Top {len(top_startups)} matches for your skills today</p>
</header>

<div class="fb">
  <input type="text" id="search" placeholder="Search by name or description..." oninput="filterTable()">
  <select id="srcFilter" onchange="filterTable()">
    <option value="">All sources</option>
    {filter_opts}
  </select>
  <select id="scFilter" onchange="filterTable()">
    <option value="0">All scores</option>
    <option value="70">70%+</option>
    <option value="40">40%+</option>
    <option value="1">1%+</option>
  </select>
  <span class="ct" id="count">0 startups</span>
</div>

<div class="mg">{cards}</div>

<div class="all-s">
  <h2>All Startups</h2>
  <p class="hint">Filtered from the day's scrape. <a href="startups.csv" style="color:#2563eb">Download CSV</a></p>
  <div class="tw">
    <table>
      <thead><tr>
        <th>Name</th><th>URL</th><th>Description</th><th>Source</th><th>Date</th><th>Score</th>
      </tr></thead>
      <tbody id="tbody">{all_rows}</tbody>
    </table>
  </div>
</div>

<footer>
  Startup Signal — <a href="https://github.com/Lawrencium-103/startup-signal">source</a>
</footer>
</div>

<script>
const DATA = {json.dumps([
    {"n": s.get("name", ""), "d": (s.get("description") or "")[:200],
     "s": s.get("source", ""), "t": s.get("extracted_at", ""),
     "sc": s.get("match_score", -1)}
    for s in (all_startups or [])
])};
function filterTable(){{
  var q=document.getElementById('search').value.toLowerCase().trim();
  var src=document.getElementById('srcFilter').value;
  var minSc=parseInt(document.getElementById('scFilter').value)||0;
  var tb=document.getElementById('tbody'); var rows=tb.querySelectorAll('tr'); var vis=0;
  for(var i=0;i<rows.length;i++){{
    var r=rows[i]; var d=DATA[i]||{{}};
    var show=true;
    if(q && d.n.toLowerCase().indexOf(q)===-1 && d.d.toLowerCase().indexOf(q)===-1) show=false;
    if(src && d.s!==src) show=false;
    if(d.sc<minSc) show=false;
    r.classList.toggle('hidden',!show);
    if(show) vis++;
  }}
  document.getElementById('count').textContent=vis+' startups';
}}
filterTable();
</script>
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
