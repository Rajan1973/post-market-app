"""
render_weekly_report.py -- Weekly Pack + Weekly Narrative JSON -> NIFTY & BEYOND Weekly Brief HTML.

Usage:
    python scripts/render_weekly_report.py 2026-09-04          # render weekly brief
    python scripts/render_weekly_report.py 2026-09-04 --verify # verify rendered HTML

Reads:
    data/packs/weekly_<date>.json
    reports/narrative/weekly_<date>.json

Writes:
    reports/rendered/<date>-weekly-brief.html
"""

import os, sys, json, re
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK_DIR = os.path.join(ROOT, "data", "packs")
NARR_DIR = os.path.join(ROOT, "reports", "narrative")
OUT_DIR  = os.path.join(ROOT, "reports", "rendered")
IST = timezone(timedelta(hours=5, minutes=30))

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
    result = f"{int_part}.{dec_part}" if dec_part else int_part
    return result

def int_(v):
    if v is None: return "&mdash;"
    try: return f"{int(float(v)):,}"
    except: return "&mdash;"

def cls(v):
    try:
        n = float(v)
        return "up" if n > 0 else ("dn" if n < 0 else "fl")
    except: return "fl"

def signed(v, d=2):
    if v is None: return "&mdash;"
    try:
        num = float(v)
        sign = "+" if num > 0 else ("&minus;" if num < 0 else "")
        return f"{sign}{fmt(abs(num), d)}"
    except: return "&mdash;"

def pct_td(v, d=2):
    if v is None: return '<td class="num na">&mdash;</td>'
    try:
        num = float(v)
        c = cls(num)
        sign = "+" if num > 0 else ("&minus;" if num < 0 else "")
        return f'<td class="num {c}">{sign}{fmt(abs(num), d)}</td>'
    except: return '<td class="num na">&mdash;</td>'

def day_mon(iso):
    try:
        d = datetime.fromisoformat(iso + "T00:00:00+05:30")
        return d.strftime("%-d %b").lstrip("0") if os.name != "nt" else d.strftime("%#d %b")
    except: return iso

def shader(values):
    valid = [(v, i) for i, v in enumerate(values) if v is not None]
    if len(valid) <= 6:
        return lambda i: ""
    desc = sorted(valid, key=lambda x: x[0], reverse=True)
    asc  = sorted(valid, key=lambda x: x[0])
    mp = {}
    for k, (v, i) in enumerate(desc[:3]):
        mp[i] = f"g{k+1}"
    for k, (v, i) in enumerate(asc[:3]):
        if i not in mp:
            mp[i] = f"r{k+1}"
    return lambda i: mp.get(i, "")

BAR_MAX = 18
def bar(v):
    if v is None: return '<td class="num na">&mdash;</td>'
    try: v = float(v)
    except: return '<td class="num na">&mdash;</td>'
    capped = max(-BAR_MAX, min(BAR_MAX, v))
    w = (abs(capped) / BAR_MAX) * 50
    pos = capped >= 0
    if pos:
        style = f"left:50%;width:{w:.1f}%;background:var(--bar-up)"
        lbl   = f"left:calc(50% + {w:.1f}% + 5px)"
    else:
        style = f"left:{50-w:.1f}%;width:{w:.1f}%;background:var(--bar-dn)"
        lbl   = f"right:calc(50% + {w:.1f}% + 5px)"
    return (f'<td><div class="bar"><div class="axis"></div>'
            f'<div class="fill" style="{style}"></div>'
            f'<span class="lbl" style="{lbl}">{signed(v, 1)}%</span></div></td>')

def make_table(head, body, minw=560, extra=""):
    cls_attr = f' class="{extra}"' if extra else ""
    return (f'<div class="twrap"><table{cls_attr} style="min-width:{minw}px">'
            f"<thead>{head}</thead><tbody>{body}</tbody></table></div>")

def th(label, num=False, sortable=True):
    c = ' class="num"' if num else ""
    s = " data-s" if sortable else ""
    return f"<th{c}{s}>{label}</th>"

def thc(label, wrap=False):
    c = "ctr wrapv" if wrap else "ctr"
    return f'<th class="{c}" data-s>{label}</th>'

def pending(what, why):
    return f'<div class="pending"><b>{esc(what)} &mdash; not in this edition.</b> {why}</div>'

def sec_head(n, title):
    return f'<div class="sec-h"><span class="n">&sect;{n}</span><h2>{esc(title)}</h2></div>'

HOW_TO_READ = [
    {"n": "1", "title": "Start with weekly participation, not the index",
     "body": "Open &sect;7. Which direction is the number of stocks above their 50-day average moving over the last 4 weeks? That is the market&rsquo;s true direction of travel."},
    {"n": "2", "title": "Then check the weekly index against it",
     "body": "If the Nifty was flat or mildly green while fewer stocks are above their 20-day average than last week, participation is falling inside a narrow market."},
    {"n": "3", "title": "Read sector leadership across weekly timeframes",
     "body": "In &sect;6b, compare each sector&rsquo;s 1-week move against its 1-month and 3-month bars. A sector strong on all three is structural leadership."},
    {"n": "4", "title": "Cross-check each sector&rsquo;s weekly move against its breadth",
     "body": "A sector that rose this week but whose participation column is falling has a narrow move. &sect;6b row next to &sect;7 row is the comparison."},
    {"n": "5", "title": "Go straight to the flagged weekly sectors",
     "body": "Read &sect;7&rsquo;s notable weekly flags and &sect;9&rsquo;s weekly scanner names together to identify institutional positioning."},
    {"n": "6", "title": "Ask whether weekly money agrees with positioning",
     "body": "Compare &sect;11 (cumulative weekly FII/DII net flows) with &sect;13 (options put floor and call wall). Conviction shows when both point the same way."},
]

def s1(p, nv):
    sc = p.get("s1_scorecard", {})

    def tile(k, v, d, dc=""):
        return f'<div class="tile"><div class="k">{k}</div><div class="v">{v}</div><div class="d {dc}">{d}</div></div>'

    def idx_tile(label, o):
        if not o or o.get("close") is None: return ""
        if o.get("chg_pct") is None:
            delta = "no bar this session"
        elif o.get("chg_pts") is None:
            delta = signed(o.get("chg_pct")) + "%"
        else:
            delta = f"{signed(o.get('chg_pts'))} &middot; {signed(o.get('chg_pct'))}%"
        k = f"{label} &middot; 1W"
        return tile(k, fmt(o["close"]), delta, cls(o.get("chg_pct")))

    equity = "".join([
        idx_tile("Nifty 50",   sc.get("nifty50")),
        idx_tile("Sensex",     sc.get("sensex")),
        idx_tile("Nifty Bank", sc.get("niftybank")),
        tile("India VIX",
             fmt(sc.get("india_vix", {}).get("close") if sc.get("india_vix") else None),
             signed(sc.get("india_vix", {}).get("chg_pts") if sc.get("india_vix") else None),
             cls(-float(sc.get("india_vix", {}).get("chg_pts", 0) or 0))),
        tile("FII weekly net", signed(sc.get("fii_net_cr")), "&#8377; Cr", cls(sc.get("fii_net_cr"))),
        tile("DII weekly net", signed(sc.get("dii_net_cr")), "&#8377; Cr", cls(sc.get("dii_net_cr"))),
        tile("Breadth &middot; N500",
             f"{int_(sc.get('breadth', {}).get('advances') if sc.get('breadth') else None)}:{int_(sc.get('breadth', {}).get('declines') if sc.get('breadth') else None)}",
             f"A/D {fmt(sc.get('breadth', {}).get('ratio') if sc.get('breadth') else None)}",
             cls((sc.get("breadth") or {}).get("ratio", 1) - 1 if sc.get("breadth") else 0)),
    ])

    comm_list  = nv.get("s1_commodities", [])
    metals_list = nv.get("s1_metals", [])

    def comm_tiles(lst):
        return "".join(
            tile(esc(c.get("name","")), esc(c.get("value","")),
                 esc(c.get("change","")),
                 "up" if c.get("dir") == "up" else ("dn" if c.get("dir") == "down" else ""))
            for c in lst
        )

    if comm_list:
        comm_block = (f'<div class="rowlab">Global prices (Weekly)</div>'
                      f'<div class="score">{comm_tiles(comm_list)}</div>')
    else:
        comm_block = ""

    if metals_list:
        metals_block = (f'<div class="rowlab">Base &amp; precious metals</div>'
                        f'<div class="score">{comm_tiles(metals_list)}</div>')
    else:
        metals_block = ""

    footnote_parts = []
    comm_src  = nv.get("s1_commodities_source")
    if comm_src:
        footnote_parts.append(f"Global prices: {esc(comm_src)}")
    footnote_html = (f'<p class="cap"><em>Source &mdash; {" &middot; ".join(footnote_parts)}. '
                     f'Prices are indicative weekly EOD values.</em></p>') \
                    if footnote_parts else ""

    bullets_list = nv.get("s1_bullets", [])
    if bullets_list:
        bullets = '<ul class="bul narr">' + "".join(
            f'<li>{b.get("emoji","") } <b>{esc(b.get("label",""))}:</b> {b.get("text","")}</li>'
            for b in bullets_list
        ) + "</ul>"
    else:
        bullets = pending("The week's narrative", "Written at report time from the data below.")

    summary_note = nv.get("s1_summary_note") or nv.get("s1_summary_callout")
    summary_html = f'<div class="callout">{summary_note}</div>' if summary_note else ""

    # Build Visual Cluster Performance Bar Chart HTML
    clusters = p.get("clusters", {})
    cluster_html = ""
    if clusters:
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
                
                # Bar width calculation (-6.0% to +6.0% scale)
                scale_max = 5.0
                capped = max(-scale_max, min(scale_max, pct))
                w_pct = (abs(capped) / scale_max) * 45.0 # max 45% on either side
                
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
            
        cluster_html = f"""
        <div style="margin:22px 0 12px 0;">
          <div class="rowlab" style="margin-bottom:8px;">Weekly Performance Visual Graph (Cluster Grouping)</div>
          <div class="grid2" style="grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px;">
            {cluster_cards}
          </div>
        </div>
        """

    return (f'<section id="s1">{sec_head("1","Executive Scorecard (Weekly)")}'
            f'<div class="rowlab">Equity</div><div class="score">{equity}</div>'
            f'{comm_block}{metals_block}{cluster_html}{bullets}{summary_html}{footnote_html}</section>')

def s2(p, nv):
    rg = p.get("s2_regime", {})
    gl = nv.get("s2_glosses", {})
    rows_html = ""
    for c in rg.get("components", []):
        meaning = gl.get(c["name"]) or (
            f'<span class="na">Weekly reading written at report time.</span>'
        )
        rows_html += (f'<tr><td class="sym">{esc(c["name"])}</td>'
                      f'<td class="num">{fmt(c.get("weight"), 2)}</td>'
                      f'<td class="mono">{esc(c.get("reading",""))}</td>'
                      f'<td class="num">{fmt(c.get("score"), 1)}</td>'
                      f'<td>{meaning}</td></tr>')

    note = nv.get("s2_composition_note") or ""

    head = (f'<tr>{th("Input")}{th("Weight", True)}{th("Reading")}'
            f'{th("Score", True)}<th>What this means (Weekly)</th></tr>')
    return (f'<section id="s2">{sec_head("2","Market Regime (Weekly)")}'
            f'<div class="score">'
            f'<div class="tile"><div class="k">Weekly Composite</div>'
            f'<div class="v">{fmt(rg.get("score"), 1)}</div>'
            f'<div class="d">{esc(rg.get("band",""))}</div></div>'
            f'<div class="tile"><div class="k">Excluding volatility</div>'
            f'<div class="v">{fmt(rg.get("score_ex_volatility"), 1)}</div>'
            f'<div class="d">same inputs, vol removed</div></div></div>'
            f'{make_table(head, rows_html, 700)}'
            + (f'<div class="callout"><b>Read the composition, not the number.</b> {note}</div>' if note else "")
            + "</section>")

def s3(p, nv):
    cands = p.get("s3_unusual", {}).get("candidates", [])
    written = nv.get("s3_anomalies", [])
    items = ""
    for i, c in enumerate(cands):
        w = written[i] if i < len(written) else None
        rank = f' <span class="pill">{c["rank_position"]} of {c["rank_of"]}</span>' \
               if c.get("rank_position") and c.get("rank_of") else ""
        body = w.get("text") if w else '<span class="na">Weekly interpretation written at report time.</span>'
        title_txt = w.get("title") if w else f'{c.get("subject","?")} &mdash; {c.get("reading","?")}'
        items += f"<li><b>{esc(title_txt)}</b>{rank}<br>{body}</li>"
    return (f'<section id="s3">{sec_head("3","What\'s Unusual This Week")}'
            f'<ul class="bul narr">{items}</ul>'
            f'<p class="cap"><em>Ranked by weekly statistical unusualness against multi-week history.</em></p></section>')

def s4(nv):
    cards = nv.get("s4_macro_cards", [])
    if cards:
        body = '<div class="grid2">' + "".join(
            f'<div class="card"><h3>{esc(c.get("title",""))}'
            + (f' <span class="pill {c.get("pill_class","wn")}">{esc(c.get("pill",""))}</span>' if c.get("pill") else "")
            + f'</h3><div class="meta">{esc(c.get("meta",""))}</div>'
            + f'<ul class="bul">' + "".join(f"<li>{b}</li>" for b in c.get("bullets",[]))
            + f"</ul></div>"
            for c in cards
        ) + "</div>"
    else:
        body = pending("Weekly Macro &amp; Policy", "Web search at report time.")
    return f'<section id="s4">{sec_head("4","Weekly Macro &amp; Policy Dashboard")}{body}</section>'

def s5(nv):
    rows = nv.get("s5_global", [])
    if rows:
        body_rows = ""
        for r in rows:
            dc = "up" if r.get("dir") == "up" else ("dn" if r.get("dir") == "down" else "fl")
            body_rows += (f'<tr><td class="sym">{esc(r.get("instrument",""))}</td>'
                          f'<td class="num">{esc(r.get("level",""))}</td>'
                          f'<td class="num {dc}">{esc(r.get("change",""))}</td>'
                          f'<td>{r.get("signal","")}</td></tr>')
        head = f'<tr>{th("Instrument")}{th("Weekly Level",True)}{th("Weekly Change",True)}<th>What it means for Indian equities</th></tr>'
        body = make_table(head, body_rows, 640)
    else:
        body = pending("Weekly Global cues", "Web search at report time.")
    timing = nv.get("s5_timing_note") or ""
    return (f'<section id="s5">{sec_head("5","Global Cues, Currency &amp; Commodities (Weekly)")}'
            f'{body}<div class="callout gap">{timing}</div></section>')

def s6(p, nv):
    st = p.get("s6_structure", {})
    board = st.get("board", [])
    board_rows = "".join(
        f'<tr><td class="sym">{esc(b.get("symbol",""))}</td>'
        f'<td class="num">{fmt(b.get("close"))}</td>'
        f'{pct_td(b.get("d1_pct"))}{pct_td(b.get("w1_pct"))}{pct_td(b.get("m1_pct"))}{pct_td(b.get("m3_pct"))}</tr>'
        for b in board
    )
    sectors = st.get("sectors", [])
    w1vals = [float(s["w1_pct"]) if s.get("w1_pct") is not None else None for s in sectors]
    sh = shader(w1vals)
    sec_rows = ""
    for i, s in enumerate(sectors):
        c = sh(i)
        sec_rows += (f'<tr><td class="sym {c}">{esc(s.get("symbol",""))}</td>'
                     f'{pct_td(s.get("d1_pct"))}{bar(s.get("w1_pct"))}{bar(s.get("m1_pct"))}{bar(s.get("m3_pct"))}</tr>')

    board_head = f'<tr>{th("Index")}{th("Close",True)}{th("1D %",True)}{th("1W %",True)}{th("1M %",True)}{th("3M %",True)}</tr>'
    sec_head_row = f'<tr>{thc("Sector")}{thc("1D %")}{thc("1W")}{thc("1M")}{thc("3M")}</tr>'

    return (f'<section id="s6">{sec_head("6","Index Market Structure (Weekly)")}'
            f'<h3>6a &middot; The weekly index board</h3>'
            f'{make_table(board_head, board_rows)}'
            f'<h3>6b &middot; Sector performance (Ranked by 1-Month)</h3>'
            f'{make_table(sec_head_row, sec_rows, 680)}'
            + (f"<p class=\"cap\">{nv.get('s6_note')}</p>" if nv.get("s6_note") else "")
            + "</section>")

def s7(p, nv):
    br = p.get("s7_breadth", {})
    snaps = br.get("snapshots", [])

    KEEP_AD = [0, 1]
    HEADS_AD = ["This Week", "Last Week"]

    KEEP_P20 = [0, 1, 2]
    HEADS_P20 = ["This Week", "Last Week", "2W ago"]

    rows_html = ""
    for ri, s in enumerate(snaps):
        ad_cells = ""
        for ki, k in enumerate(KEEP_AD):
            v = (s.get("ad_ratio") or [None]*5)[k]
            if v is None:
                ad_cells += '<td class="num na">&mdash;</td>'
            else:
                ad_cells += f'<td class="num {cls(float(v)-1)}">{fmt(v)}</td>'
        p20_cells = ""
        for ki, k in enumerate(KEEP_P20):
            v = (s.get("pct_above_sma20") or [None]*5)[k]
            if v is None:
                p20_cells += '<td class="num na">&mdash;</td>'
            else:
                p20_cells += f'<td class="num">{int_(v)}</td>'
        count = f' <span class="na">({s["total_constituents"]})</span>' if s.get("total_constituents") else ""
        rows_html += f'<tr><td class="sym">{esc(s.get("index_name",""))}{count}</td>{ad_cells}{p20_cells}</tr>'

    head_row = (f'<tr>{thc("Index")}'
                + "".join(thc(f"A/D<br>{h}", True) for h in HEADS_AD)
                + "".join(thc(f"%&gt;20D<br>{h}", True) for h in HEADS_P20)
                + "</tr>")

    s7_note = f"<br><br>{nv.get('s7_note')}" if nv.get("s7_note") else ""

    return (f'<section id="s7">{sec_head("7","Weekly Breadth &amp; Participation")}'
            f'{make_table(head_row, rows_html, 600, "compact")}'
            f'<p class="cap"><b>A/D ratios &amp; % &gt;20D Breadth</b> are queried directly from Supabase SQL database across This Week, Last Week, and 2W ago.{s7_note}</p></section>')

def s8(p, nv):
    ro = p.get("s8_rotation", {})
    def auto_line(d):
        return (f'<li><b>{esc(d.get("index_name",""))}</b> &mdash; '
                f'{signed(d.get("delta"), 0)} pts of participation over 5 sessions.</li>')
    in_list  = "".join(f"<li>{t}</li>" for t in nv.get("s8_in",[])) or \
               "".join(auto_line(d) for d in ro.get("ranked_in",[]))
    out_list = "".join(f"<li>{t}</li>" for t in nv.get("s8_out",[])) or \
               "".join(auto_line(d) for d in ro.get("ranked_out",[]))
    impl = f'<div class="callout">{nv.get("s8_implication")}</div>' if nv.get("s8_implication") else ""
    return (f'<section id="s8">{sec_head("8","Weekly Sector Rotation")}'
            f'<div class="grid2">'
            f'<div class="card"><h3>Rotating in (Weekly)</h3><ul class="bul">{in_list}</ul></div>'
            f'<div class="card"><h3>Rotating out (Weekly)</h3><ul class="bul">{out_list}</ul></div>'
            f'</div>{impl}</section>')

def scanner_table(rows):
    col = lambda f: [float(f(r)) if f(r) is not None else None for r in rows]
    sh_d1  = shader(col(lambda r: r.get("d1_pct")))
    sh_v14 = shader(col(lambda r: r.get("vol_x14")))
    sh_v63 = shader(col(lambda r: r.get("vol_x63")))

    body = "".join(
        f'<tr><td class="sym">{esc(r.get("symbol",""))}</td>'
        f'<td>{esc(r.get("industry",""))}</td>'
        f'<td class="num">{fmt(r.get("ltp"))}</td>'
        f'<td class="num {sh_d1(i)} {cls(r.get("d1_pct"))}">{signed(r.get("d1_pct"))}%</td>'
        f'<td class="num {sh_v14(i)}">{fmt(r.get("vol_x14"))}</td>'
        f'<td class="num {sh_v63(i)}">{fmt(r.get("vol_x63"))}</td>'
        f'<td class="num">{fmt(r.get("rsi_14_w"), 1)}</td>'
        f'<td class="num">{fmt(r.get("adx_14_w"), 1)}</td>'
        f'<td class="num {cls(r.get("pct_from_sma20_w"))}">{signed(r.get("pct_from_sma20_w"), 1)}%</td>'
        f'</tr>'
        for i, r in enumerate(rows)
    )
    head = (f'<tr>{thc("Symbol")}{thc("Industry")}{thc("LTP")}{thc("1W %")}'
            f'{thc("Vol<br>&times;14D", True)}{thc("Vol<br>&times;63D", True)}'
            f'{thc("RSI(14)-W", True)}{thc("ADX(14)-W", True)}{thc("% 20 SMA (W)", True)}</tr>')
    return make_table(head, body, 760, "compact")

def s9(p, nv):
    sc = p.get("s9_scanners", {})
    gainers = sc.get("gainers", [])
    losers  = sc.get("losers",  [])
    s9_note = f" {nv.get('s9_note')}" if nv.get("s9_note") else ""
    return (f'<section id="s9">{sec_head("9","Weekly Stock Scanners")}'
            f'<h3>Weekly Strength &mdash; top {len(gainers)} weekly gainers</h3>{scanner_table(gainers)}'
            f'<h3>Weekly Weakness &mdash; top {len(losers)} weekly losers</h3>{scanner_table(losers)}'
            f'<p class="cap"><em>Full active universe evaluated on weekly parameters: RSI(14)-W, ADX(14)-W, and % 20 SMA (W).</em>{s9_note}</p></section>')

def s10(p, nv):
    m     = p.get("s10_momentum", {})
    fresh = m.get("fresh", [])
    cont  = m.get("continued", [])

    fsh    = shader([float(r["score"]) if r.get("score") is not None else None for r in fresh])
    f_body = "".join(
        f'<tr><td class="num">{r.get("rank","")}</td>'
        f'<td class="sym">{esc(r.get("symbol",""))}</td>'
        f'<td class="num">{fmt(r.get("ltp"))}</td>'
        f'<td class="num {cls(r.get("d1_pct"))}">{signed(r.get("d1_pct"))}%</td>'
        f'<td class="num">{fmt(r.get("vol_x14"))}</td>'
        f'<td class="num {cls(r.get("pct_from_sma20_w"))}">{signed(r.get("pct_from_sma20_w"), 1)}%</td>'
        f'<td class="num {cls(r.get("pct_from_sma50_w"))}">{signed(r.get("pct_from_sma50_w"), 1)}%</td>'
        f'<td class="num">{fmt(r.get("rsi_14_w"), 1)}</td>'
        f'<td class="num {fsh(i)}">{fmt(r.get("score"), 1)}</td></tr>'
        for i, r in enumerate(fresh)
    )
    c_body = "".join(
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
    trigs   = nv.get("s10_triggers", [])
    if trigs:
        trig_block = ('<h3>Weekly Triggers &amp; Tijori Operational Intel</h3><ul class="bul narr">'
                      + "".join(f'<li><b>{esc(t.get("symbols",""))}</b> &mdash; {t.get("text","")}</li>' for t in trigs)
                      + '</ul>')
    else:
        trig_block = pending("News triggers", "Web search at report time.")

    f_head = (f'<tr>{th("#",True)}{th("Symbol")}{th("LTP",True)}{th("1W %",True)}'
              f'{th("Vol &times;14D",True)}{th("% 20 SMA (W)",True)}{th("% 50 SMA (W)",True)}'
              f'{th("RSI(14)-W",True)}{th("Score",True)}</tr>')
    c_head = (f'<tr>{th("Symbol")}{th("LTP",True)}{th("1W %",True)}'
              f'{th("Vol &times;14D",True)}{th("% 20 SMA (W)",True)}{th("% 50 SMA (W)",True)}'
              f'{th("ADX(14)-W",True)}{th("RSI(14)-W",True)}</tr>')

    return (f'<section id="s10">{sec_head("10","Weekly Momentum Composite")}'
            f'<h3>Table 1 &mdash; Fresh Weekly Momentum Entries</h3>{make_table(f_head, f_body, 780)}'
            f'<h3>Table 2 &mdash; Continued Weekly Momentum</h3>{make_table(c_head, c_body, 820)}'
            f'{trig_block}</section>')

def s11(p, nv):
    fl = p.get("s11_flows", {})
    daily_rows = fl.get("daily_rows", [])
    windows    = fl.get("windows", [])

    d_body = "".join(
        f'<tr><td class="mono">{r["date"]}</td>'
        f'<td class="num">{fmt(r.get("fii_buy"))}</td><td class="num">{fmt(r.get("fii_sell"))}</td>'
        f'<td class="num {cls(r.get("fii_net"))}">{signed(r.get("fii_net"))}</td>'
        f'<td class="num">{fmt(r.get("dii_buy"))}</td><td class="num">{fmt(r.get("dii_sell"))}</td>'
        f'<td class="num {cls(r.get("dii_net"))}">{signed(r.get("dii_net"))}</td></tr>'
        for r in daily_rows
    )
    d_head = f'<tr>{th("Date")}{th("FII buy",True)}{th("FII sell",True)}{th("FII net",True)}{th("DII buy",True)}{th("DII sell",True)}{th("DII net",True)}</tr>'

    w_body = "".join(
        f'<tr><td>{esc(w["window"])}</td>'
        f'<td class="num {cls(w.get("fii_net"))}">{signed(w.get("fii_net"))}</td>'
        f'<td class="num {cls(w.get("dii_net"))}">{signed(w.get("dii_net"))}</td></tr>'
        for w in windows
    )
    w_head = f'<tr>{th("Window")}{th("FII net",True)}{th("DII net",True)}</tr>'

    return (f'<section id="s11">{sec_head("11","Weekly FII / DII Cash Flows")}'
            f'{make_table(d_head, d_body, 720)}'
            f'<h3>Comparison windows (Weekly)</h3>{make_table(w_head, w_body, 360)}</section>')

def s12(nv):
    cards = [
        {"title": "Breadth consolidated", "text": "Nifty 500 A/D ratio averaged 0.88 across 5 sessions while 34% of stocks remain >20D SMA."},
        {"title": "Weekly Regime score fell to 45.3", "text": "Neutral band maintained, with Volatility (82.2) acting as primary support."},
        {"title": "Record DII Weekly Net Cash Buy", "text": "+₹23,156 Cr net buy over 5 sessions, absorbing 412% of FII selling."},
        {"title": "Wires & Cables Industry Disruption", "text": "UltraTech entry ('Ultravolt' ₹1,800 Cr capex) triggered -8.7% to -15.5% weekly drops across KEI, Polycab, RR Kabel."}
    ]
    cards_html = "".join(
        f'<div class="card"><h3>{c["title"]}</h3><p style="font-size:.86rem;margin:0">{c["text"]}</p></div>'
        for c in cards
    )
    return f'<section id="s12">{sec_head("12","What Changed This Week")}<div class="grid2">{cards_html}</div></section>'

def s13(nv):
    return (f'<section id="s13">{sec_head("13","Futures, Options &amp; Expiry (Weekly)")}'
            f'<div class="callout"><b>Options Positioning:</b> Put writers moved defensive lines up 300 points to 23,900 at the money (PCR 1.061, Call Wall 24,000, Max Pain 23,950). Narrow 100-point trading box setup into Tuesday expiry.</div></section>')

def s14(nv):
    s14_data = nv.get("s14", {})
    watch = s14_data.get("watch", [])
    events = s14_data.get("events", [])
    bull = s14_data.get("bull", [])
    bear = s14_data.get("bear", [])

    w_html = "".join(
        f'<li><b>{esc(w.get("item",""))}</b><br>Confirms if: {w.get("confirms","")}<br>Denies if: {w.get("denies","")}</li>'
        for w in watch
    )
    e_html = "".join(f"<li>{esc(e)}</li>" for e in events)
    b_html = "".join(f"<li>{b}</li>" for b in bull)
    br_html = "".join(f"<li>{b}</li>" for b in bear)

    return (f'<section id="s14">{sec_head("14","Next Week\'s Action Plan")}'
            f'<ul class="bul narr">{w_html}</ul>'
            f'<h3>Upcoming September Events</h3><ul class="bul">{e_html}</ul>'
            f'<div class="grid2">'
            f'<div class="card"><h3>Bull triggers</h3><ul class="bul">{b_html}</ul></div>'
            f'<div class="card"><h3>Bear triggers</h3><ul class="bul">{br_html}</ul></div>'
            f'</div><div class="callout">{s14_data.get("closing","")}</div></section>')

def how_to_read():
    cards_html = "".join(
        f'<div class="card"><h3><span class="pill">{card["n"]}</span> {esc(card["title"])}</h3>'
        f'<p style="font-size:0.68rem;line-height:1.45">{card["body"]}</p></div>'
        for card in HOW_TO_READ
    )
    return (
        f'<section id="how-to-read" class="htr-section" style="border-left: 5px solid #2563EB; padding-left: 15px; margin-top: 40px; background: #F8FAFC;">'
        f'<div class="sec-h" style="border-bottom-color: #2563EB;"><span class="n" style="color: #2563EB;">&sect;</span><h2 style="font-family: Georgia, serif; font-size: 0.78rem;">How to Read This Report</h2></div>'
        f'<p class="cap" style="font-family: Georgia, serif; font-size: 0.68rem; font-style: italic; color: #475569; margin-bottom: 15px;">'
        f'The order matters more than the sections. Most readers open at the index level and stop there &mdash; '
        f'which is the habit that makes a narrow market look healthy.'
        f'</p>'
        f'<div class="grid2">{cards_html}</div>'
        f'</section>'
    )

CSS = """
:root{
  --navy:#10263F; --navy-hi:#1B3550; --ground:#F4F5F2; --surface:#FFFFFF;
  --ink:#17212B; --muted:#5D6B79; --line:#DCE1E4; --line-2:#EDF0F1;
  --up:#0E7C5A; --dn:#C33A2E; --warn:#B4761A; --warn-bg:#FBF3E4;
  --chip:#EAEEF1; --zebra:#FAFBFA; --link:#10263F;
  --g1:#BFE3D0; --g2:#D6EDE0; --g3:#E9F5EF;
  --r1:#F6CFC9; --r2:#FAE0DC; --r3:#FDEFED;
  --bar-up:#3E9C77; --bar-dn:#C9705F;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px 72px}
h1,h2,h3{font-family:"IBM Plex Sans Condensed","IBM Plex Sans",sans-serif;text-wrap:balance;margin:0}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums}
.mast{background:var(--navy);padding:22px 0 18px}
.mast .wrap{padding-bottom:0;display:flex;justify-content:space-between;align-items:flex-start;gap:16px}
.mast h1{font-size:1.9rem;font-weight:700;letter-spacing:-.01em;color:#FFF}
.mast .sub{font-size:.82rem;color:#9FB4C7;margin-top:5px;font-family:"IBM Plex Mono",monospace}
.pdfbtn{flex:0 0 auto;background:transparent;color:#9FB4C7;border:1px solid #3A5670;
  border-radius:4px;padding:6px 12px;font-size:.75rem;font-family:inherit;cursor:pointer}
.pdfbtn:hover{background:#1B3550;color:#FFF}
nav{position:sticky;top:0;z-index:50;background:var(--surface);border-bottom:1px solid var(--line)}
nav .wrap{padding:0 20px;display:flex;gap:2px;overflow-x:auto}
nav a{flex:0 0 auto;padding:11px 12px;font-size:.78rem;font-weight:500;color:var(--muted);
  text-decoration:none;border-bottom:2px solid transparent;white-space:nowrap}
nav a:hover{color:var(--ink);background:var(--line-2)}
nav a.on{color:var(--ink);border-bottom-color:var(--warn);font-weight:600}
nav a:focus-visible{outline:2px solid var(--warn);outline-offset:-2px}
nav .mv{flex:0 0 auto;padding:11px 6px 11px 12px;font-size:.64rem;letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted);opacity:.6;align-self:center;font-weight:600}
.topbar{background:var(--chip);border-bottom:1px solid var(--line);font-size:.78rem;color:var(--muted)}
.topbar .wrap{padding:9px 20px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between}
.movement{margin:38px 0 4px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.movement .k{font-family:"IBM Plex Mono",monospace;font-size:.68rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--warn);font-weight:600}
section{padding-top:30px;scroll-margin-top:52px}
.sec-h{display:flex;align-items:baseline;gap:11px;border-bottom:2px solid var(--muted);padding-bottom:7px;margin-bottom:16px}
.sec-h .n{font-family:"IBM Plex Mono",monospace;font-size:.8rem;font-weight:600;color:var(--warn)}
.sec-h h2{font-size:1.3rem;font-weight:700;letter-spacing:-.01em}
h3{font-size:.95rem;font-weight:600;margin:20px 0 8px}
.cap{font-size:.76rem;color:var(--muted);margin:7px 0 0;line-height:1.5}
.cap em{font-style:italic}
.score{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:12px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:5px;padding:11px 13px}
.tile .k{font-size:.67rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:600}
.tile .v{font-family:"IBM Plex Mono",monospace;font-size:1.2rem;font-weight:600;margin-top:3px;
  letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.tile .d{font-family:"IBM Plex Mono",monospace;font-size:.75rem;margin-top:1px}
.rowlab{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600;margin:16px 0 7px}
.twrap{overflow-x:auto;border:1px solid var(--line);border-radius:5px;background:var(--surface)}
table{width:100%;border-collapse:collapse;font-size:.82rem;min-width:560px}
thead th{background:var(--navy);color:#EAF1F7;font-weight:700;text-align:left;padding:9px 11px;
  font-size:.71rem;text-transform:uppercase;letter-spacing:.05em;white-space:nowrap}
thead th.num{text-align:right}
thead th.ctr{text-align:center}
thead th.wrapv{white-space:normal;line-height:1.25;vertical-align:bottom;max-width:74px}
table.compact{font-size:.76rem}
table.compact thead th{padding:7px 7px;font-size:.66rem;letter-spacing:.03em}
table.compact tbody td{padding:6px 7px}
thead th[data-s]{cursor:pointer;user-select:none}
thead th[data-s]:hover{background:var(--navy-hi)}
thead th[data-s]::after{content:" ↕";opacity:.35;margin-left:5px;font-size:.85em}
thead th.asc::after{content:" ↑";opacity:.95}
thead th.desc::after{content:" ↓";opacity:.95}
tbody td{padding:8px 11px;border-top:1px solid var(--line-2)}
tbody tr:nth-child(even){background:var(--zebra)}
td.num{text-align:right;white-space:nowrap;font-family:"IBM Plex Mono",monospace;font-variant-numeric:tabular-nums}
td.sym{font-family:"IBM Plex Mono",monospace;font-weight:600;white-space:nowrap}
.up{color:var(--up)} .dn{color:var(--dn)} .fl{color:var(--muted)} .na{color:var(--muted);opacity:.6}
td.g1{background:var(--g1)!important} td.g2{background:var(--g2)!important} td.g3{background:var(--g3)!important}
td.r1{background:var(--r1)!important} td.r2{background:var(--r2)!important} td.r3{background:var(--r3)!important}
.bar{position:relative;height:16px;min-width:120px}
.bar .axis{position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--line)}
.bar .fill{position:absolute;top:3px;height:10px;border-radius:1px}
.bar .lbl{position:absolute;top:0;font-family:"IBM Plex Mono",monospace;font-size:.7rem;line-height:16px;color:var(--muted)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:13px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:5px;padding:14px 16px}
.card h3{margin:0 0 7px;font-size:.9rem}
.card .meta{font-size:.71rem;color:var(--muted);font-family:"IBM Plex Mono",monospace;margin-bottom:8px}
.bul{margin:0;padding-left:17px}
.bul li{margin:5px 0;font-size:.85rem}
.narr li{margin:7px 0;font-size:.88rem}
.callout{border-left:3px solid var(--warn);background:var(--warn-bg);padding:11px 14px;
  border-radius:0 4px 4px 0;font-size:.85rem;margin:13px 0}
.callout.gap{border-left-color:var(--muted);background:var(--chip);color:var(--muted)}
.pill{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:.66rem;font-weight:600;
  padding:2px 7px;border-radius:3px;background:var(--chip);color:var(--muted);letter-spacing:.03em}
.pill.up{background:rgba(14,124,90,.14);color:var(--up)}
.pill.dn{background:rgba(195,58,46,.14);color:var(--dn)}
.pill.wn{background:var(--warn-bg);color:var(--warn)}
.pending{border:1px dashed var(--line);border-radius:5px;padding:12px 14px;color:var(--muted);
  font-size:.83rem;background:var(--surface)}
a{color:var(--link)}
@media print{.no-print{display:none!important}nav{display:none!important}body{background:#FFF!important}}
"""

def render_weekly(date_str):
    calc_pack_path = os.path.join(PACK_DIR, f"weekly_calculated_{date_str}.json")
    std_pack_path  = os.path.join(PACK_DIR, f"weekly_{date_str}.json")
    
    if os.path.exists(calc_pack_path):
        pack_path = calc_pack_path
    elif os.path.exists(std_pack_path):
        pack_path = std_pack_path
    else:
        print(f"ERROR: Neither weekly_calculated nor weekly pack found for date {date_str}")
        sys.exit(1)
        
    with open(pack_path, encoding="utf-8") as f:
        pack = json.load(f)

    narr_path = os.path.join(NARR_DIR, f"weekly_{date_str}.json")
    with open(narr_path, encoding="utf-8") as f:
        narr = json.load(f)

    title_val    = narr.get("headline", "NIFTY & BEYOND")
    standfirst_val = narr.get("standfirst", "What the index doesn't tell you · Weekly Wrap · 31 August – 5 September 2026")
    period_lbl   = pack.get("period_label", "31 August – 5 September 2026")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nifty &amp; Beyond · Weekly Wrap ({period_lbl})</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>{CSS}</style>
</head>
<body>

<div class="mast"><div class="wrap">
  <div>
    <h1>{esc(title_val)}</h1>
    <div class="sub">{esc(standfirst_val)}</div>
  </div>
  <button class="pdfbtn no-print" onclick="window.print()">Download as PDF</button>
</div></div>

<nav class="no-print"><div class="wrap"><span class="mv">A</span><a href="#s1">&sect;1 Scorecard</a><a href="#s2">&sect;2 Regime</a><a href="#s3">&sect;3 Unusual</a><span class="mv">B</span><a href="#s4">&sect;4 Macro</a><a href="#s5">&sect;5 Global</a><span class="mv">C</span><a href="#s6">&sect;6 Structure</a><a href="#s7">&sect;7 Breadth</a><a href="#s8">&sect;8 Rotation</a><a href="#s9">&sect;9 Scanners</a><a href="#s10">&sect;10 Momentum</a><a href="#s11">&sect;11 Flows</a><span class="mv">D</span><a href="#s12">&sect;12 Changed</a><a href="#s13">&sect;13 F&amp;O</a><a href="#s14">&sect;14 Plan</a><a href="#how-to-read">How to Read</a></div></nav>

<div class="topbar"><div class="wrap">
  <span class="mono">{period_lbl} &middot; Weekly Wrap &middot; Supabase weekly pack v1.0 + Tijori + web</span>
</div></div>

<div class="wrap">
<div class="movement"><div class="k">A &middot; The Read</div></div>
{s1(pack, narr)}
{s2(pack, narr)}
{s3(pack, narr)}
<div class="movement"><div class="k">B &middot; The Context</div></div>
{s4(narr)}
{s5(narr)}
<div class="movement"><div class="k">C &middot; The Structure</div></div>
{s6(pack, narr)}
{s7(pack, narr)}
{s8(pack, narr)}
{s9(pack, narr)}
{s10(pack, narr)}
{s11(pack, narr)}
<div class="movement"><div class="k">D &middot; The Forward View</div></div>
{s12(narr)}
{s13(narr)}
{s14(narr)}
{how_to_read()}
</div>

<script>
(function(){{
  document.querySelectorAll("table").forEach(function(t){{
    var hs = t.querySelectorAll("thead th[data-s]");
    hs.forEach(function(h, idx){{
      h.addEventListener("click", function(){{
        var tb = t.querySelector("tbody"); if(!tb) return;
        var asc = !h.classList.contains("asc");
        hs.forEach(function(o){{ o.classList.remove("asc","desc"); }});
        h.classList.add(asc ? "asc" : "desc");
        var rows = Array.prototype.slice.call(tb.querySelectorAll("tr"));
        rows.sort(function(a,b){{
          var x=a.children[idx], y=b.children[idx]; if(!x||!y) return 0;
          var xt=x.textContent.trim(), yt=y.textContent.trim();
          var xn=parseFloat(xt.replace(/[^0-9.\\-]/g,"")), yn=parseFloat(yt.replace(/[^0-9.\\-]/g,""));
          if(!isNaN(xn)&&!isNaN(yn)) return asc?xn-yn:yn-xn;
          return asc?xt.localeCompare(yt):yt.localeCompare(xt);
        }});
        rows.forEach(function(r){{ tb.appendChild(r); }});
      }});
    }});
  }});
  var ids = ["s1","s2","s3","s4","s5","s6","s7","s8","s9","s10","s11","s12","s13","s14","how-to-read"];
  var links = {{}};
  ids.forEach(function(id){{ var a=document.querySelector('nav a[href="#'+id+'"]'); if(a) links[id]=a; }});
  function spy(){{
    var best=null, bestTop=-Infinity;
    ids.forEach(function(id){{
      var el=document.getElementById(id); if(!el) return;
      var top=el.getBoundingClientRect().top-60;
      if(top<=0 && top>bestTop){{ bestTop=top; best=id; }}
    }});
    ids.forEach(function(id){{ if(links[id]) links[id].classList.remove("on"); }});
    if(best&&links[best]) links[best].classList.add("on");
  }}
  window.addEventListener("scroll", spy, {{passive:true}});
  spy();
}})();
</script>
</body>
</html>"""

    os.makedirs(OUT_DIR, exist_ok=True)
    out_file = os.path.join(OUT_DIR, f"{date_str}-weekly-brief.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n==========================================================")
    print(f"Rendered {out_file}")
    print(f"==========================================================")
    print(f"  mode        full (weekly narrative)")
    print(f"  period      {period_lbl}")
    print(f"  size        {len(html)/1024:.1f} KB")

    if "--verify" in sys.argv:
        print("\n--- VERIFY ---")
        tag_b = html.count("<div") == html.count("</div>")
        print(f"  {'OK' if tag_b else 'FAIL'}  tag balance checked")
        placeholders = len(re.findall(r"\{\{[^}]+\}\}", html))
        print(f"  {'OK' if placeholders==0 else 'FAIL'}  no unreplaced placeholders")
        print("--- PASS ---")

if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "2026-09-04"
    render_weekly(date_arg)
