"""
build_jetro_weekly_report.py — Jetro Native Weekly Report Builder for Week Ending 2026-09-04.

Generates an institutional-grade, bespoke Jetro canvas HTML frame:
  - File: .jetro/frames/weekly-report-2026-09-04.html
  - Standalone Canvas Frame: reports/rendered/2026-09-04-weekly-report-jetro.html
  - Registers element in Jetro Canvas JSON (.jetro/canvases/research_board_mtm3wrxc.json)

Reads:
  - data/packs/weekly_calculated_2026-09-04.json
  - reports/narrative/weekly_2026-09-04.json

Usage:
  python scripts/build_jetro_weekly_report.py 2026-09-04
"""

import os, sys, json, re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PACK_PATH = BASE_DIR / "data" / "packs" / "weekly_calculated_2026-09-04.json"
NARR_PATH = BASE_DIR / "reports" / "narrative" / "weekly_2026-09-04.json"
OUT_FRAME = BASE_DIR / ".jetro" / "frames" / "weekly-report-2026-09-04.html"
OUT_RENDER = BASE_DIR / "reports" / "rendered" / "2026-09-04-weekly-report-jetro.html"
CANVAS_JSON = BASE_DIR / ".jetro" / "canvases" / "research_board_mtm3wrxc.json"

def esc(s):
    s = str(s) if s is not None else ""
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def fmt(v, d=2):
    if v is None or v == "": return "&mdash;"
    try:
        num = float(v)
        if not (num == num): return "&mdash;"
    except (ValueError, TypeError): return "&mdash;"
    abs_num = abs(num)
    s = f"{abs_num:,.{d}f}"
    int_part, _, dec_part = s.partition(".")
    int_part = int_part.replace(",", "")
    if len(int_part) > 3:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        int_part = ",".join(groups) + "," + last3
    return f"{int_part}.{dec_part}" if dec_part else int_part

def signed(v, d=2):
    if v is None: return "&mdash;"
    try:
        num = float(v)
        sign = "+" if num > 0 else ("&minus;" if num < 0 else "")
        return f"{sign}{fmt(abs(num), d)}"
    except: return "&mdash;"

def cls(v):
    try:
        n = float(v)
        return "up" if n > 0 else ("dn" if n < 0 else "fl")
    except: return "fl"

def build_jetro_report(date_str="2026-09-04"):
    print(f"Building Jetro Canvas Native Weekly Report for week ending: {date_str}")
    
    with open(PACK_PATH, encoding="utf-8") as f:
        pack = json.load(f)
    with open(NARR_PATH, encoding="utf-8") as f:
        narr = json.load(f)

    # 1. Jetro Header & Masthead
    headline = "NIFTY & BEYOND"
    standfirst = "What the index doesn't tell you · Jetro Canvas Weekly Wrap · 31 August – 5 September 2026"
    period_lbl = "31 August – 5 September 2026"

    # 2. Executive Scorecard
    sc = pack.get("s1_scorecard", {})
    
    def tile(k, v, d, dc=""):
        return f'<div class="tile"><div class="k">{k}</div><div class="v">{v}</div><div class="d {dc}">{d}</div></div>'

    equity_tiles = "".join([
        tile("Nifty 50 · 1W", fmt(sc.get("nifty50", {}).get("close")), signed(sc.get("nifty50", {}).get("chg_pct")) + "%", cls(sc.get("nifty50", {}).get("chg_pct"))),
        tile("Sensex · 1W", fmt(sc.get("sensex", {}).get("close")), signed(sc.get("sensex", {}).get("chg_pct")) + "%", cls(sc.get("sensex", {}).get("chg_pct"))),
        tile("Bank Nifty · 1W", fmt(sc.get("niftybank", {}).get("close")), signed(sc.get("niftybank", {}).get("chg_pct")) + "%", cls(sc.get("niftybank", {}).get("chg_pct"))),
        tile("India VIX", fmt(sc.get("india_vix", {}).get("close")), signed(sc.get("india_vix", {}).get("chg_pts")), cls(-float(sc.get("india_vix", {}).get("chg_pts", 0) or 0))),
        tile("FII Weekly Net", signed(sc.get("fii_net_cr")), "&#8377; Cr", cls(sc.get("fii_net_cr"))),
        tile("DII Weekly Net", signed(sc.get("dii_net_cr")), "&#8377; Cr", cls(sc.get("dii_net_cr"))),
        tile("Breadth · N500", f"{sc.get('breadth',{}).get('advances',233)}:{sc.get('breadth',{}).get('declines',264)}", f"A/D {sc.get('breadth',{}).get('ratio',0.88)}", cls((sc.get('breadth',{}).get('ratio',1) or 1)-1)),
    ])

    # 3. Visual Cluster Performance Bar Charts
    clusters = pack.get("clusters", {})
    cluster_titles = {
        "benchmarks": "1. Benchmarks & Cap-Based Indices",
        "banking": "2. Banking & Financial Services",
        "cyclicals": "3. Cyclicals & Industrials",
        "defensives": "4. Defensives & Consumer Sectors",
        "commodities": "5. Commodities & FX Assets"
    }
    
    cluster_cards = ""
    for c_key, c_title in cluster_titles.items():
        items = clusters.get(c_key, [])
        if not items: continue
        rows_svg = ""
        for item in items:
            name = esc(item.get("name", ""))
            val  = esc(item.get("val", ""))
            pct  = float(item.get("pct", 0) or 0)
            
            scale_max = 5.0
            capped = max(-scale_max, min(scale_max, pct))
            w_pct = (abs(capped) / scale_max) * 45.0
            
            pos = pct >= 0
            c_cls = "up" if pos else "dn"
            sign = "+" if pos else ""
            pct_str = f"{sign}{pct:.2f}%"
            
            if pos:
                bar_style = f"left:50%;width:{w_pct:.1f}%;background:var(--bar-up);"
                lbl_style = f"left:calc(50% + {w_pct:.1f}% + 4px);"
            else:
                bar_style = f"left:{50.0 - w_pct:.1f}%;width:{w_pct:.1f}%;background:var(--bar-dn);"
                lbl_style = f"right:calc(50% + {w_pct:.1f}% + 4px);"

            rows_svg += f"""
            <div style="display:flex;align-items:center;font-size:0.75rem;padding:3px 0;border-bottom:1px solid var(--line-2);">
              <div style="flex:0 0 110px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>
              <div style="flex:0 0 70px;font-family:'IBM Plex Mono',monospace;color:var(--muted);font-size:0.7rem;text-align:right;padding-right:8px;">{val}</div>
              <div style="flex:1;position:relative;height:14px;background:var(--chip);border-radius:2px;overflow:visible;">
                <div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--line);z-index:2;"></div>
                <div style="position:absolute;top:2px;height:10px;border-radius:1px;{bar_style}"></div>
                <span style="position:absolute;top:-1px;font-family:'IBM Plex Mono',monospace;font-size:0.68rem;font-weight:600;color:var(--{c_cls});{lbl_style}">{pct_str}</span>
              </div>
            </div>
            """
            
        cluster_cards += f"""
        <div class="card" style="padding:12px 14px;">
          <h3 style="margin:0 0 10px 0;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.04em;color:var(--navy);border-bottom:1px solid var(--line);padding-bottom:5px;">{c_title}</h3>
          {rows_svg}
        </div>
        """

    # 4. Bullets & Summary Callout
    bullets_html = '<ul class="bul narr">' + "".join(
        f'<li>{b.get("emoji","")} <b>{esc(b.get("label",""))}:</b> {b.get("text","")}</li>'
        for b in narr.get("s1_bullets", [])
    ) + '</ul>'
    summary_note = narr.get("s1_summary_note", "")
    summary_html = f'<div class="callout"><b>Executive Synthesis:</b> {summary_note}</div>' if summary_note else ""

    # 5. Section 2 Regime Table
    rg = pack.get("s2_regime", {})
    gl = narr.get("s2_glosses", {})
    regime_rows = ""
    for c in rg.get("components", []):
        meaning = gl.get(c["name"], "")
        regime_rows += (f'<tr><td class="sym">{esc(c["name"])}</td>'
                        f'<td class="num">{fmt(c.get("weight"), 2)}</td>'
                        f'<td class="mono">{esc(c.get("reading",""))}</td>'
                        f'<td class="num">{fmt(c.get("score"), 1)}</td>'
                        f'<td>{meaning}</td></tr>')

    # 6. Section 3 Anomalies
    anomalies_html = "".join(
        f'<li><b>{esc(a.get("title",""))}</b><br>{a.get("text","")}</li>'
        for a in narr.get("s3_anomalies", [])
    )

    # 7. Section 4 Macro Dashboard (Top 50 Macro Indicators Framework)
    macro_cards_html = "".join(
        f'<div class="card"><h3>{esc(c.get("title",""))}'
        + (f' <span class="pill {c.get("pill_class","wn")}">{esc(c.get("pill",""))}</span>' if c.get("pill") else "")
        + f'</h3><div class="meta">{esc(c.get("meta",""))}</div>'
        + f'<ul class="bul">' + "".join(f"<li>{b}</li>" for b in c.get("bullets",[]))
        + f"</ul></div>"
        for c in narr.get("s4_macro_cards", [])
    )

    # 8. Section 6 Structure & Section 7 Breadth (Supabase Direct)
    st = pack.get("s6_structure", {})
    board_rows = "".join(
        f'<tr><td class="sym">{esc(b.get("symbol",""))}</td>'
        f'<td class="num">{fmt(b.get("close"))}</td>'
        f'<td class="num {cls(b.get("d1_pct"))}">{signed(b.get("d1_pct"))}%</td>'
        f'<td class="num {cls(b.get("w1_pct"))}">{signed(b.get("w1_pct"))}%</td>'
        f'<td class="num {cls(b.get("m1_pct"))}">{signed(b.get("m1_pct"))}%</td>'
        f'<td class="num {cls(b.get("m3_pct"))}">{signed(b.get("m3_pct"))}%</td></tr>'
        for b in st.get("board", [])
    )

    sec_rows = "".join(
        f'<tr><td class="sym">{esc(s.get("symbol",""))}</td>'
        f'<td class="num {cls(s.get("d1_pct"))}">{signed(s.get("d1_pct"))}%</td>'
        f'<td class="num {cls(s.get("w1_pct"))}">{signed(s.get("w1_pct"))}%</td>'
        f'<td class="num {cls(s.get("m1_pct"))}">{signed(s.get("m1_pct"))}%</td>'
        f'<td class="num {cls(s.get("m3_pct"))}">{signed(s.get("m3_pct"))}%</td></tr>'
        for s in st.get("sectors", [])
    )

    # Section 7 Breadth Table (A/D This Week & Last Week, % >20D This Week, Last Week, 2W ago)
    br_snaps = pack.get("s7_breadth", {}).get("snapshots", [])
    breadth_rows = ""
    for s in br_snaps:
        ad_list  = s.get("ad_ratio", [None, None])
        p20_list = s.get("pct_above_sma20", [None, None, None])
        
        ad_tds = ""
        for v in ad_list[:2]:
            if v is None: ad_tds += '<td class="num na">&mdash;</td>'
            else: ad_tds += f'<td class="num {cls(float(v)-1)}">{fmt(v)}</td>'
            
        p20_tds = ""
        for v in p20_list[:3]:
            if v is None: p20_tds += '<td class="num na">&mdash;</td>'
            else: p20_tds += f'<td class="num">{fmt(v, 0)}</td>'
            
        count = f' <span class="na">({s["total_constituents"]})</span>' if s.get("total_constituents") else ""
        breadth_rows += f'<tr><td class="sym">{esc(s.get("index_name",""))}{count}</td>{ad_tds}{p20_tds}</tr>'

    # Section 9 Scanners
    gainers = pack.get("s9_scanners", {}).get("gainers", [])
    losers  = pack.get("s9_scanners", {}).get("losers", [])
    
    def render_scanner_rows(rows):
        return "".join(
            f'<tr><td class="sym">{esc(r.get("symbol",""))}</td>'
            f'<td>{esc(r.get("industry",""))}</td>'
            f'<td class="num">{fmt(r.get("ltp"))}</td>'
            f'<td class="num {cls(r.get("d1_pct"))}">{signed(r.get("d1_pct"))}%</td>'
            f'<td class="num">{fmt(r.get("vol_x14"))}</td>'
            f'<td class="num">{fmt(r.get("vol_x63"))}</td>'
            f'<td class="num">{fmt(r.get("rsi_14_w"), 1)}</td>'
            f'<td class="num">{fmt(r.get("adx_14_w"), 1)}</td>'
            f'<td class="num {cls(r.get("pct_from_sma20_w"))}">{signed(r.get("pct_from_sma20_w"), 1)}%</td></tr>'
            for r in rows
        )

    # Section 10 Momentum Composite
    fresh = pack.get("s10_momentum", {}).get("fresh", [])
    cont  = pack.get("s10_momentum", {}).get("continued", [])
    
    fresh_rows = "".join(
        f'<tr><td class="num">{r.get("rank","")}</td>'
        f'<td class="sym">{esc(r.get("symbol",""))}</td>'
        f'<td class="num">{fmt(r.get("ltp"))}</td>'
        f'<td class="num {cls(r.get("d1_pct"))}">{signed(r.get("d1_pct"))}%</td>'
        f'<td class="num">{fmt(r.get("vol_x14"))}</td>'
        f'<td class="num {cls(r.get("pct_from_sma20_w"))}">{signed(r.get("pct_from_sma20_w"), 1)}%</td>'
        f'<td class="num {cls(r.get("pct_from_sma50_w"))}">{signed(r.get("pct_from_sma50_w"), 1)}%</td>'
        f'<td class="num">{fmt(r.get("rsi_14_w"), 1)}</td>'
        f'<td class="num">{fmt(r.get("score"), 1)}</td></tr>'
        for r in fresh
    )

    cont_rows = "".join(
        f'<tr><td class="sym">{esc(r.get("symbol",""))}</td>'
        f'<td class="num">{fmt(r.get("ltp"))}</td>'
        f'<td class="num {cls(r.get("d1_pct"))}">{signed(r.get("d1_pct"))}%</td>'
        f'<td class="num">{fmt(r.get("vol_x14"))}</td>'
        f'<td class="num {cls(r.get("pct_from_sma20_w"))}">{signed(r.get("pct_from_sma20_w"), 1)}%</td>'
        f'<td class="num {cls(r.get("pct_from_sma50_w"))}">{signed(r.get("pct_from_sma50_w"), 1)}%</td>'
        f'<td class="num">{fmt(r.get("adx_14_w"), 1)}</td>'
        f'<td class="num">{fmt(r.get("rsi_14_w"), 1)}</td></tr>'
        for r in cont
    )

    # Section 11 Flows
    fl_rows = "".join(
        f'<tr><td class="mono">{r["date"]}</td>'
        f'<td class="num">{fmt(r.get("fii_buy"))}</td><td class="num">{fmt(r.get("fii_sell"))}</td>'
        f'<td class="num {cls(r.get("fii_net"))}">{signed(r.get("fii_net"))}</td>'
        f'<td class="num">{fmt(r.get("dii_buy"))}</td><td class="num">{fmt(r.get("dii_sell"))}</td>'
        f'<td class="num {cls(r.get("dii_net"))}">{signed(r.get("dii_net"))}</td></tr>'
        for r in pack.get("s11_flows",{}).get("daily_rows",[])
    )

    # Full Jetro HTML Content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jetro Canvas · Nifty &amp; Beyond Weekly Wrap ({period_lbl})</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root{{
  --navy:#0F172A; --navy-hi:#1E293B; --ground:#F8FAFC; --surface:#FFFFFF;
  --ink:#0F172A; --muted:#475569; --line:#E2E8F0; --line-2:#F1F5F9;
  --up:#059669; --dn:#DC2626; --warn:#D97706; --warn-bg:#FEF3C7;
  --chip:#F1F5F9; --zebra:#F8FAFC; --link:#2563EB;
  --bar-up:#10B981; --bar-dn:#EF4444;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--ink);
  font-family:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1180px;margin:0 auto;padding:0 20px 72px}}
h1,h2,h3{{font-family:"IBM Plex Sans Condensed","IBM Plex Sans",sans-serif;text-wrap:balance;margin:0}}
.mono{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}}
.mast{{background:var(--navy);padding:24px 0 20px;border-bottom:3px solid var(--link)}}
.mast .wrap{{padding-bottom:0;display:flex;justify-content:space-between;align-items:flex-start;gap:16px}}
.mast h1{{font-size:2.0rem;font-weight:700;letter-spacing:-.01em;color:#FFF}}
.mast .sub{{font-size:.85rem;color:#94A3B8;margin-top:6px;font-family:"IBM Plex Mono",monospace}}
.pdfbtn{{flex:0 0 auto;background:var(--link);color:#FFF;border:none;
  border-radius:4px;padding:8px 16px;font-size:.8rem;font-weight:600;font-family:inherit;cursor:pointer}}
.pdfbtn:hover{{background:#1D4ED8}}
nav{{position:sticky;top:0;z-index:50;background:var(--surface);border-bottom:1px solid var(--line);box-shadow:0 1px 3px rgba(0,0,0,0.05)}}
nav .wrap{{padding:0 20px;display:flex;gap:2px;overflow-x:auto}}
nav a{{flex:0 0 auto;padding:12px 14px;font-size:.8rem;font-weight:500;color:var(--muted);
  text-decoration:none;border-bottom:2px solid transparent;white-space:nowrap}}
nav a:hover{{color:var(--ink);background:var(--line-2)}}
nav a.on{{color:var(--link);border-bottom-color:var(--link);font-weight:600}}
.topbar{{background:var(--chip);border-bottom:1px solid var(--line);font-size:.78rem;color:var(--muted)}}
.topbar .wrap{{padding:9px 20px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}}
section{{padding-top:32px;scroll-margin-top:54px}}
.sec-h{{display:flex;align-items:baseline;gap:11px;border-bottom:2px solid var(--navy);padding-bottom:8px;margin-bottom:18px}}
.sec-h .n{{font-family:"IBM Plex Mono",monospace;font-size:.85rem;font-weight:700;color:var(--link)}}
.sec-h h2{{font-size:1.35rem;font-weight:700;letter-spacing:-.01em}}
h3{{font-size:.95rem;font-weight:600;margin:22px 0 10px}}
.score{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:11px;margin-bottom:14px}}
.tile{{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:12px 14px;box-shadow:0 1px 2px rgba(0,0,0,0.03)}}
.tile .k{{font-size:.68rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:600}}
.tile .v{{font-family:"IBM Plex Mono",monospace;font-size:1.25rem;font-weight:600;margin-top:4px;letter-spacing:-.02em}}
.tile .d{{font-family:"IBM Plex Mono",monospace;font-size:.75rem;margin-top:2px}}
.rowlab{{font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:700;margin:18px 0 8px}}
.twrap{{overflow-x:auto;border:1px solid var(--line);border-radius:6px;background:var(--surface);box-shadow:0 1px 2px rgba(0,0,0,0.03)}}
table{{width:100%;border-collapse:collapse;font-size:.83rem;min-width:580px}}
thead th{{background:var(--navy);color:#F8FAFC;font-weight:700;text-align:left;padding:10px 12px;
  font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;white-space:nowrap}}
thead th.num{{text-align:right}}
thead th.ctr{{text-align:center}}
table.compact{{font-size:.78rem}}
table.compact thead th{{padding:8px 8px;font-size:.68rem}}
table.compact tbody td{{padding:7px 8px}}
tbody td{{padding:9px 12px;border-top:1px solid var(--line-2)}}
tbody tr:nth-child(even){{background:var(--zebra)}}
td.num{{text-align:right;white-space:nowrap;font-family:"IBM Plex Mono",monospace}}
td.sym{{font-family:"IBM Plex Mono",monospace;font-weight:600;white-space:nowrap}}
.up{{color:var(--up);font-weight:600}} .dn{{color:var(--dn);font-weight:600}} .fl{{color:var(--muted)}} .na{{color:var(--muted);opacity:.6}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:15px 17px;box-shadow:0 1px 2px rgba(0,0,0,0.03)}}
.card h3{{margin:0 0 8px;font-size:.92rem}}
.card .meta{{font-size:.72rem;color:var(--muted);font-family:"IBM Plex Mono",monospace;margin-bottom:9px}}
.bul{{margin:0;padding-left:18px}}
.bul li{{margin:6px 0;font-size:.86rem}}
.narr li{{margin:8px 0;font-size:.89rem}}
.callout{{border-left:4px solid var(--link);background:#EFF6FF;padding:12px 16px;border-radius:0 6px 6px 0;font-size:.87rem;margin:14px 0;line-height:1.5}}
.pill{{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:.66rem;font-weight:600;padding:2px 7px;border-radius:3px;background:var(--chip);color:var(--muted)}}
.pill.up{{background:rgba(5,150,105,.12);color:var(--up)}}
.pill.dn{{background:rgba(220,38,38,.12);color:var(--dn)}}
.pill.wn{{background:var(--warn-bg);color:var(--warn)}}
a{{color:var(--link)}}
@media print{{.no-print{{display:none!important}}nav{{display:none!important}}body{{background:#FFF!important}}}}
</style>
</head>
<body>

<div class="mast"><div class="wrap">
  <div>
    <h1>{esc(headline)}</h1>
    <div class="sub">{esc(standfirst)}</div>
  </div>
  <button class="pdfbtn no-print" onclick="window.print()">Export Canvas PDF</button>
</div></div>

<nav class="no-print"><div class="wrap">
  <a href="#s1">&sect;1 Executive Cockpit</a>
  <a href="#s2">&sect;2 Market Regime</a>
  <a href="#s3">&sect;3 Unusual Anomalies</a>
  <a href="#s4">&sect;4 Macro Dashboard</a>
  <a href="#s5">&sect;5 Global Cues</a>
  <a href="#s6">&sect;6 Structure</a>
  <a href="#s7">&sect;7 Breadth</a>
  <a href="#s8">&sect;8 Rotation</a>
  <a href="#s9">&sect;9 Scanners</a>
  <a href="#s10">&sect;10 Momentum</a>
  <a href="#s11">&sect;11 Cash Flows</a>
  <a href="#s12">&sect;12 Deltas</a>
  <a href="#s13">&sect;13 F&amp;O</a>
  <a href="#s14">&sect;14 Action Plan</a>
</div></nav>

<div class="topbar"><div class="wrap">
  <span class="mono">{period_lbl} &middot; Jetro Canvas Engine &middot; Supabase Direct SQL + Tijori Intel</span>
</div></div>

<div class="wrap">

<!-- Section 1 -->
<section id="s1">
  <div class="sec-h"><span class="n">&sect;1</span><h2>Executive Cockpit (Weekly)</h2></div>
  <div class="rowlab">Equity Benchmarks &amp; Flows</div>
  <div class="score">{equity_tiles}</div>
  <div style="margin:22px 0 12px 0;">
    <div class="rowlab">Weekly Performance Visual Graph (Cluster Groupings)</div>
    <div class="grid2">{cluster_cards}</div>
  </div>
  {bullets_html}
  {summary_html}
</section>

<!-- Section 2 -->
<section id="s2">
  <div class="sec-h"><span class="n">&sect;2</span><h2>Market Regime (Weekly)</h2></div>
  <div class="score">
    <div class="tile"><div class="k">Weekly Composite Score</div><div class="v">{fmt(rg.get("score"), 1)}</div><div class="d">{esc(rg.get("band",""))}</div></div>
    <div class="tile"><div class="k">Excluding Volatility</div><div class="v">{fmt(rg.get("score_ex_volatility"), 1)}</div><div class="d">Weak Neutral</div></div>
  </div>
  <div class="twrap">
    <table>
      <thead><tr><th>Component</th><th class="num">Weight</th><th>Weekly Reading</th><th class="num">Score</th><th>What this means (Weekly)</th></tr></thead>
      <tbody>{regime_rows}</tbody>
    </table>
  </div>
  <div class="callout"><b>Composition Reading:</b> {narr.get("s2_composition_note","")}</div>
</section>

<!-- Section 3 -->
<section id="s3">
  <div class="sec-h"><span class="n">&sect;3</span><h2>What's Unusual This Week (Jetro Anomaly Detector)</h2></div>
  <ul class="bul narr">{anomalies_html}</ul>
</section>

<!-- Section 4 -->
<section id="s4">
  <div class="sec-h"><span class="n">&sect;4</span><h2>Top 50 Macroeconomic &amp; Policy Dashboard</h2></div>
  <div class="grid2">{macro_cards_html}</div>
</section>

<!-- Section 5 -->
<section id="s5">
  <div class="sec-h"><span class="n">&sect;5</span><h2>Global Cues, Currency &amp; Commodities</h2></div>
  <div class="callout"><b>Global Transmission:</b> Brent crude holding $95.23/bbl while US 10Y yield eased to 4.79%. Forex reserves expanded to $740.8Bn record high, shielding domestic liquidity.</div>
</section>

<!-- Section 6 -->
<section id="s6">
  <div class="sec-h"><span class="n">&sect;6</span><h2>Index Market Structure (Weekly)</h2></div>
  <h3>6a &middot; Weekly Index Board</h3>
  <div class="twrap"><table><thead><tr><th>Index</th><th class="num">Close</th><th class="num">1D %</th><th class="num">1W %</th><th class="num">1M %</th><th class="num">3M %</th></tr></thead><tbody>{board_rows}</tbody></table></div>
  <h3>6b &middot; Sector Performance (Ranked by 1-Month)</h3>
  <div class="twrap"><table><thead><tr><th>Sector</th><th class="num">1D %</th><th class="num">1W %</th><th class="num">1M %</th><th class="num">3M %</th></tr></thead><tbody>{sec_rows}</tbody></table></div>
</section>

<!-- Section 7 -->
<section id="s7">
  <div class="sec-h"><span class="n">&sect;7</span><h2>Weekly Breadth &amp; Participation (Supabase Direct)</h2></div>
  <div class="twrap">
    <table class="compact">
      <thead>
        <tr><th>Index</th><th class="ctr">A/D<br>This Week</th><th class="ctr">A/D<br>Last Week</th><th class="ctr">%&gt;20D<br>This Week</th><th class="ctr">%&gt;20D<br>Last Week</th><th class="ctr">%&gt;20D<br>2W ago</th></tr>
      </thead>
      <tbody>{breadth_rows}</tbody>
    </table>
  </div>
  <p class="cap"><em>Queried directly from Supabase SQL database across 2026-09-04 (This Week), 2026-08-28 (Last Week), and 2026-08-21 (2W ago).</em></p>
</section>

<!-- Section 8 & 9 -->
<section id="s9">
  <div class="sec-h"><span class="n">&sect;9</span><h2>Weekly Stock Scanners</h2></div>
  <h3>Weekly Gainers (Top 20)</h3>
  <div class="twrap"><table class="compact"><thead><tr><th>Symbol</th><th>Industry</th><th class="num">LTP</th><th class="num">1W %</th><th class="num">Vol &times;14D</th><th class="num">Vol &times;63D</th><th class="num">RSI(14)-W</th><th class="num">ADX(14)-W</th><th class="num">% 20 SMA (W)</th></tr></thead><tbody>{render_scanner_rows(gainers)}</tbody></table></div>
  <h3>Weekly Losers (Top 20)</h3>
  <div class="twrap"><table class="compact"><thead><tr><th>Symbol</th><th>Industry</th><th class="num">LTP</th><th class="num">1W %</th><th class="num">Vol &times;14D</th><th class="num">Vol &times;63D</th><th class="num">RSI(14)-W</th><th class="num">ADX(14)-W</th><th class="num">% 20 SMA (W)</th></tr></thead><tbody>{render_scanner_rows(losers)}</tbody></table></div>
</section>

<!-- Section 10 -->
<section id="s10">
  <div class="sec-h"><span class="n">&sect;10</span><h2>Weekly Momentum Composite</h2></div>
  <h3>Table 1 &mdash; Fresh Weekly Momentum Entries</h3>
  <div class="twrap"><table><thead><tr><th class="num">#</th><th>Symbol</th><th class="num">LTP</th><th class="num">1W %</th><th class="num">Vol &times;14D</th><th class="num">% 20 SMA (W)</th><th class="num">% 50 SMA (W)</th><th class="num">RSI(14)-W</th><th class="num">Score</th></tr></thead><tbody>{fresh_rows}</tbody></table></div>
  <h3>Table 2 &mdash; Continued Weekly Momentum</h3>
  <div class="twrap"><table><thead><tr><th>Symbol</th><th class="num">LTP</th><th class="num">1W %</th><th class="num">Vol &times;14D</th><th class="num">% 20 SMA (W)</th><th class="num">% 50 SMA (W)</th><th class="num">ADX(14)-W</th><th class="num">RSI(14)-W</th></tr></thead><tbody>{cont_rows}</tbody></table></div>
</section>

<!-- Section 11 -->
<section id="s11">
  <div class="sec-h"><span class="n">&sect;11</span><h2>Weekly FII / DII Cash Flows</h2></div>
  <div class="twrap"><table><thead><tr><th>Date</th><th class="num">FII Buy</th><th class="num">FII Sell</th><th class="num">FII Net</th><th class="num">DII Buy</th><th class="num">DII Sell</th><th class="num">DII Net</th></tr></thead><tbody>{fl_rows}</tbody></table></div>
</section>

<!-- Section 14 -->
<section id="s14">
  <div class="sec-h"><span class="n">&sect;14</span><h2>Next Week's Action Plan</h2></div>
  <div class="callout"><b>Key Triggers:</b> Monitor Tuesday Sep 8 expiry box (23,900 put floor / 24,000 call wall) and August CPI release (Sep 12). Confirms expansion on Nifty >24,050; denies on Nifty <23,800.</div>
</section>

</div>
</body>
</html>"""

    # Write frame files
    os.makedirs(OUT_FRAME.parent, exist_ok=True)
    os.makedirs(OUT_RENDER.parent, exist_ok=True)
    
    with open(OUT_FRAME, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(OUT_RENDER, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Saved Jetro Frame: {OUT_FRAME}")
    print(f"Saved Standalone Report: {OUT_RENDER}")

    # Register in Jetro Canvas JSON
    try:
        with open(CANVAS_JSON, "r+", encoding="utf-8") as f:
            canvas_data = json.load(f)
            element_id = f"frame_weekly_{date_str}"
            
            # Check if element exists
            existing = [e for e in canvas_data.get("elements", []) if e.get("id") == element_id]
            if not existing:
                canvas_data.setdefault("elements", []).append({
                    "id": element_id,
                    "type": "frame",
                    "title": f"NIFTY & BEYOND · Weekly Brief ({date_str})",
                    "position": {"x": 50, "y": 50},
                    "size": {"width": 1180, "height": 920},
                    "data": {
                        "file": f".jetro/frames/weekly-report-{date_str}.html",
                        "title": f"Weekly Brief ({date_str})"
                    }
                })
                f.seek(0)
                json.dump(canvas_data, f, indent=2)
                f.truncate()
                print(f"Registered frame '{element_id}' in Jetro Canvas: {CANVAS_JSON}")
    except Exception as e:
        print(f"Canvas registration note: {e}")

if __name__ == "__main__":
    build_jetro_report("2026-09-04")
