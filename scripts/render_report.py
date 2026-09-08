"""
render_report.py -- Pack + narrative JSON -> NIFTY & BEYOND HTML report.

Usage:
    python scripts/render_report.py 2026-09-04          # render
    python scripts/render_report.py 2026-09-04 --stub   # write narrative skeleton
    python scripts/render_report.py 2026-09-04 --verify # verify rendered HTML
    python scripts/render_report.py                     # use latest cached pack

Reads:
    data/packs/<date>.json          (must exist -- run fetch_pack.py first)
    reports/narrative/<date>.json   (optional -- renders pending blocks if absent)

Writes:
    reports/rendered/<date>-daily-brief.html
"""
import os, sys, json, re
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK_DIR  = os.path.join(ROOT, "data", "packs")
NARR_DIR  = os.path.join(ROOT, "reports", "narrative")
OUT_DIR   = os.path.join(ROOT, "reports", "rendered")
IST = timezone(timedelta(hours=5, minutes=30))

# ── helpers ────────────────────────────────────────────────────────────────────

def esc(s):
    """HTML-escape a value from the pack. Narrative prose is NOT escaped."""
    s = str(s) if s is not None else ""
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def fmt(v, d=2):
    """Format a number with d decimals, Indian locale style, or mdash."""
    if v is None or v == "": return "&mdash;"
    try:
        num = float(v)
        if not (num == num): return "&mdash;"  # NaN
    except (ValueError, TypeError): return "&mdash;"
    # Indian number formatting: groups of 2 after the first 3
    abs_num = abs(num)
    s = f"{abs_num:,.{d}f}"
    # Python's comma formatting is Western; convert to Indian grouping
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
    """'2026-08-27' -> '27 Aug'"""
    try:
        d = datetime.fromisoformat(iso + "T00:00:00+05:30")
        return d.strftime("%-d %b").lstrip("0") if os.name != "nt" else d.strftime("%#d %b")
    except: return iso

def shader(values):
    """
    Returns a fn(i) -> css class. Top 3 get g1/g2/g3, bottom 3 get r1/r2/r3.
    Skipped for <=6 rows (would shade nearly everything - presentation rule 9).
    """
    valid = [(v, i) for i, v in enumerate(values) if v is not None]
    if len(valid) <= 6:
        return lambda i: ""
    desc = sorted(valid, key=lambda x: x[0], reverse=True)
    asc  = sorted(valid, key=lambda x: x[0])
    mp = {}
    for k, (v, i) in enumerate(desc[:3]):
        mp[i] = f"g{k+1}"
    for k, (v, i) in enumerate(asc[:3]):
        if i not in mp:  # don't overwrite a g class
            mp[i] = f"r{k+1}"
    return lambda i: mp.get(i, "")

BAR_MAX = 18
def bar(v):
    """±18% scale bar cell."""
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

# ── HOW TO READ block (renderer-owned, identical every edition) ───────────────
HOW_TO_READ = [
    {"n": "1", "title": "Start with participation, not the index",
     "body": "Open &sect;7. Which direction is the number of stocks above their 20-day average moving? That is the market&rsquo;s direction of travel, not the index close."},
    {"n": "2", "title": "Then check the index against it",
     "body": "If the Nifty rose but fewer stocks are above their 20-day average than yesterday, participation is falling inside a rising index. That divergence is the most important thing on the page."},
    {"n": "3", "title": "Read sector leadership across timeframes",
     "body": "In &sect;6b, compare each sector&rsquo;s 1-day move against its 1-week and 1-month bars. A sector strong on the day but weak on the month is a bounce. A sector strong on all three is a trend."},
    {"n": "4", "title": "Cross-check each sector&rsquo;s move against its own breadth",
     "body": "A sector that rose today but whose participation column is falling has a narrow move &mdash; a few stocks doing the work. &sect;6b row next to &sect;7 row is the comparison."},
    {"n": "5", "title": "Go straight to the flagged sectors",
     "body": "The pack has already joined breadth to the scanners for you. Read &sect;7&rsquo;s notable flags and &sect;9&rsquo;s scanner names together &mdash; that join is already done."},
    {"n": "6", "title": "Ask whether the money agrees with the positioning",
     "body": "Compare &sect;11 (what institutions bought and sold) with &sect;13 (where the derivatives positioning sits). Conviction shows when both point the same way."},
]


# ── section renderers ─────────────────────────────────────────────────────────

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
        k = f"{label} &middot; {day_mon(o['as_of'])}" if (o.get("stale") and o.get("as_of")) else label
        return tile(k, fmt(o["close"]), delta, cls(o.get("chg_pct")))

    equity = "".join([
        idx_tile("Nifty 50",   sc.get("nifty50")),
        idx_tile("Sensex",     sc.get("sensex")),
        idx_tile("Nifty Bank", sc.get("niftybank")),
        tile("India VIX",
             fmt(sc.get("india_vix", {}).get("close") if sc.get("india_vix") else None),
             signed(sc.get("india_vix", {}).get("chg_pts") if sc.get("india_vix") else None),
             cls(-float(sc.get("india_vix", {}).get("chg_pts", 0) or 0))),
        tile("FII net &middot; cash", signed(sc.get("fii_net_cr")), "&#8377; Cr", cls(sc.get("fii_net_cr"))),
        tile("DII net &middot; cash", signed(sc.get("dii_net_cr")), "&#8377; Cr", cls(sc.get("dii_net_cr"))),
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
        comm_block = (f'<div class="rowlab">Global prices</div>'
                      f'<div class="score">{comm_tiles(comm_list)}</div>')
    else:
        comm_block = (f'<div class="rowlab">Global prices</div>'
                      f'{pending("Commodity tiles", "Web-sourced at report time.")}')

    if metals_list:
        metals_block = (f'<div class="rowlab">Base &amp; precious metals</div>'
                        f'<div class="score">{comm_tiles(metals_list)}</div>')
    else:
        metals_block = ""

    # Source footnote: collect as_of / source from both lists
    footnote_parts = []
    comm_src  = nv.get("s1_commodities_source")
    metals_src = nv.get("s1_metals_source")
    if comm_src:
        footnote_parts.append(f"Global prices: {esc(comm_src)}")
    if metals_src:
        footnote_parts.append(f"Metals: {esc(metals_src)}")
    footnote_html = (f'<p class="cap"><em>Source &mdash; {" &middot; ".join(footnote_parts)}. '
                     f'Prices are indicative EOD values; not real-time quotes. '
                     f'Metal spot rates: LME official settlement (USD/tonne except Silver USD/oz); '
                     f'MCX contract prices (INR) may differ on currency and timing.</em></p>') \
                    if footnote_parts else ""

    bullets_list = nv.get("s1_bullets", [])
    if bullets_list:
        bullets = '<ul class="bul narr">' + "".join(
            f'<li>{b.get("emoji","") } <b>{esc(b.get("label",""))}:</b> {b.get("text","")}</li>'
            for b in bullets_list
        ) + "</ul>"
    else:
        bullets = pending("The day's narrative", "Written at report time from the data below.")

    summary_note = nv.get("s1_summary_note") or nv.get("s1_summary_callout")
    summary_html = f'<div class="callout">{summary_note}</div>' if summary_note else ""

    return (f'<section id="s1">{sec_head("1","Executive Scorecard")}'
            f'<div class="rowlab">Equity</div><div class="score">{equity}</div>'
            f'{comm_block}{metals_block}{bullets}{summary_html}{footnote_html}</section>')


def s2(p, nv):
    rg = p.get("s2_regime", {})
    gl = nv.get("s2_glosses", {})
    rows_html = ""
    for c in rg.get("components", []):
        meaning = gl.get(c["name"]) or (
            f'<span class="na">Plain-English reading written at report time. '
            f'Ranked {c.get("rank", {}).get("position","&mdash;")} of {c.get("rank", {}).get("of","&mdash;")}.</span>'
        )
        rows_html += (f'<tr><td class="sym">{esc(c["name"])}</td>'
                      f'<td class="num">{fmt(c.get("weight"), 2)}</td>'
                      f'<td class="mono">{esc(c.get("reading",""))}</td>'
                      f'<td class="num">{fmt(c.get("score"), 1)}</td>'
                      f'<td>{meaning}</td></tr>')

    dis = rg.get("disagreement")
    note = nv.get("s2_composition_note") or (
        (f'The components disagree by <b>{fmt(dis.get("spread"), 1)} points</b> &mdash; '
         f'{esc(dis.get("lowest",""))} is the weakest and {esc(dis.get("highest",""))} the strongest. '
         f'Excluding volatility the score reads <b>{fmt(rg.get("score_ex_volatility"), 1)}</b>.')
        if dis else ""
    )

    head = (f'<tr>{th("Input")}{th("Weight", True)}{th("Reading")}'
            f'{th("Score", True)}<th>What this means</th></tr>')
    return (f'<section id="s2">{sec_head("2","Market Regime")}'
            f'<div class="score">'
            f'<div class="tile"><div class="k">Composite</div>'
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
        body = w.get("text") if w else '<span class="na">Interpretation written at report time.</span>'
        title_txt = w.get("title") if w else f'{c.get("subject","?")} &mdash; {c.get("reading","?")}'
        items += f"<li><b>{esc(title_txt)}</b>{rank}<br>{body}</li>"
    return (f'<section id="s3">{sec_head("3","What\'s Unusual Today")}'
            f'<ul class="bul narr">{items}</ul>'
            f'<p class="cap"><em>Ranked by how unusual each reading is against its own history, '
            f'not by which number is largest. Window lengths are in the pack; ranks shown as position out of window.</em>'
            f'</p></section>')


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
        body = pending("Macro & Policy", "Web search at report time. Nothing in Supabase feeds this section.")
    return f'<section id="s4">{sec_head("4","Macro & Policy Dashboard")}{body}</section>'


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
        head = f'<tr>{th("Instrument")}{th("Level",True)}{th("Change",True)}<th>What it means for Indian equities</th></tr>'
        body = make_table(head, body_rows, 640)
    else:
        body = pending("Global cues, currency & commodities", "Web search at report time.")
    timing = nv.get("s5_timing_note") or \
        "US index closes settle <b>after</b> the Indian close. They are cues for the <i>next</i> session, not drivers of this one."
    return (f'<section id="s5">{sec_head("5","Global Cues, Currency & Commodities")}'
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
    nd = st.get("nifty_day", {})
    pos_map = {"upper_third": "the upper third", "middle_third": "the middle", "lower_third": "the lower third"}
    pos_word = pos_map.get(nd.get("close_position",""), "&mdash;")

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

    return (f'<section id="s6">{sec_head("6","Index Market Structure")}'
            f'<h3>6a &middot; The index board</h3>'
            f'{make_table(board_head, board_rows)}'
            f'<p class="cap"><b>Nifty 50 day:</b> open {fmt(nd.get("open"))} &middot; '
            f'high {fmt(nd.get("high"))} &middot; low {fmt(nd.get("low"))} &middot; '
            f'close {fmt(nd.get("close"))} &middot; range {fmt(nd.get("range_pts"))} pts, '
            f'closing in <b>{pos_word}</b> of it.<br>'
            f'<em>Table shows 1M trailing, not month-to-date (MTD).</em></p>'
            f'<h3>6b &middot; Sector performance</h3>'
            f'{make_table(sec_head_row, sec_rows, 680)}'
            f'<p class="cap"><em>All Indices Ranked by 1-month return.</em>'
            + (f" {nv.get('s6_note')}" if nv.get("s6_note") else "")
            + "</p></section>")


def s7(p, nv):
    br = p.get("s7_breadth", {})
    dates = br.get("snapshot_dates", [])
    snaps = br.get("snapshots", [])

    # D-3 dropped (index 3); keep today(0), D-1(1), D-2(2), 1W ago(4)
    KEEP = [0, 1, 2, 4]
    HEADS = ["Today", "D-1", "D-2", "1W ago"]
    SHADE_AT = [0, 3]  # shade today and 1W ago columns

    ad_cols  = [[(s.get("ad_ratio",  [None]*5) or [None]*5)[k] for s in snaps] for k in KEEP]
    p20_cols = [[(s.get("pct_above_sma20", [None]*5) or [None]*5)[k] for s in snaps] for k in KEEP]

    ad_sh  = [shader([float(v) if v is not None else None for v in col])
              if ki in SHADE_AT else (lambda i: "")
              for ki, col in enumerate(ad_cols)]
    p20_sh = [shader([float(v) if v is not None else None for v in col])
              if ki in SHADE_AT else (lambda i: "")
              for ki, col in enumerate(p20_cols)]

    rows_html = ""
    for ri, s in enumerate(snaps):
        ad_cells = ""
        for ki, k in enumerate(KEEP):
            v = (s.get("ad_ratio") or [None]*5)[k]
            if v is None:
                ad_cells += '<td class="num na">&mdash;</td>'
            else:
                ad_cells += f'<td class="num {ad_sh[ki](ri)} {cls(float(v)-1)}">{fmt(v)}</td>'
        p20_cells = ""
        for ki, k in enumerate(KEEP):
            v = (s.get("pct_above_sma20") or [None]*5)[k]
            if v is None:
                p20_cells += '<td class="num na">&mdash;</td>'
            else:
                p20_cells += f'<td class="num {p20_sh[ki](ri)}">{int_(v)}</td>'
        count = f' <span class="na">({s["total_constituents"]})</span>' if s.get("total_constituents") else ""
        rows_html += f'<tr><td class="sym">{esc(s.get("index_name",""))}{count}</td>{ad_cells}{p20_cells}</tr>'

    keep_dates = [d for i, d in enumerate(dates) if i in KEEP]
    head_row = (f'<tr>{thc("Index")}'
                + "".join(thc(f"A/D<br>{h}", True) for h in HEADS)
                + "".join(thc(f"%&gt;20D<br>{h}", True) for h in HEADS)
                + "</tr>")

    s7_note = f"<br><br>{nv.get('s7_note')}" if nv.get("s7_note") else ""

    # crosslink: pre-joined breadth × scanner data (added to pack 2026-09-03)
    # spec says "write up every notable entry; that is its whole purpose"
    notable_items = br.get("notable", [])
    crosslink_html = ""
    if notable_items:
        cards = ""
        for n in notable_items:
            idx_name   = esc(n.get("index_name", ""))
            ad_today   = n.get("ad_today")
            pct20      = n.get("pct20_today")
            delta3     = n.get("pct20_delta_3d")
            over_rep   = n.get("over_representation")
            reasons    = n.get("reasons", [])
            gainers    = n.get("scanner_gainers", [])
            losers     = n.get("scanner_losers",  [])
            hits       = n.get("scanner_hits", 0)
            total      = n.get("total_constituents")

            reasons_html = "".join(f"<li>{esc(r)}</li>" for r in reasons)
            g_html = (", ".join(f'<span class="pill up">{esc(s)}</span>' for s in gainers)
                      if gainers else "")
            l_html = (", ".join(f'<span class="pill dn">{esc(s)}</span>' for s in losers)
                      if losers else "")
            scanner_line = ""
            if hits:
                over_txt = f" &mdash; {fmt(over_rep)}x its universe share" if over_rep else ""
                scanner_line = (f'<div class="meta">{hits} of today\'s 40 scanner slots'
                                f'{" from a " + int_(total) + "-stock index" if total else ""}'
                                f'{over_txt}</div>')
            names_html = ""
            if g_html or l_html:
                names_html = (f'<div style="margin-top:6px;font-size:.8rem">'
                              + (f"Gainers: {g_html} " if g_html else "")
                              + (f"Losers: {l_html}" if l_html else "")
                              + "</div>")

            cards += (f'<div class="card">'
                      f'<h3>{idx_name}'
                      + (f' <span class="pill wn">A/D {fmt(ad_today)}</span>' if ad_today is not None else "")
                      + f'</h3>'
                      + scanner_line
                      + f'<ul class="bul">{reasons_html}</ul>'
                      + names_html
                      + f'</div>')

        crosslink_html = (f'<h3>Sector signals &mdash; breadth meets the scanners</h3>'
                          f'<p class="cap"><em>Sectors where today\'s breadth or scanner concentration '
                          f'is statistically notable. Pre-joined by the pack builder so the same event '
                          f'is not written up separately in &sect;7 and &sect;9.</em></p>'
                          f'<div class="grid3">{cards}</div>')

    return (f'<section id="s7">{sec_head("7","Breadth & Participation")}'
            f'{make_table(head_row, rows_html, 640, "compact")}'
            f'<p class="cap"><b>A/D D-1</b> is the advance/decline for yesterday. '
            f'<b>%&gt;20D D-1</b> is the percentage of stocks in that index trading above their 20-day SMA, yesterday.<br><br>'
            f'<b>A/D Today</b> tells you how the index performed today &mdash; what the advance-to-decline ratio was. '
            f'<b>%&gt;20D SMA</b> tells you what percentage of stocks in that universe is trading above its 20-day simple '
            f'moving average. Watch how the A/D ratio moved from last week to today, and how %&gt;20D SMA moved over the '
            f'same stretch &mdash; those two shaded pairs are the comparison this table exists for.<br><br>'
            f'A rising index with <b>increasing advances and more stocks above the 20D SMA</b> means broader participation '
            f'in the rally. A rising index on <b>very narrow participation</b> can instead mean index management, indecision, '
            f'or only a few sectors doing the work while the rest of the market goes nowhere.{s7_note}</p>'
            f'<p class="cap"><em>Snapshots: {" &middot; ".join(esc(d) for d in keep_dates)}. '
            f'All percentages are whole numbers. The 5-day participation change and the full SMA ladder (20/50/100/200) are '
            f'carried in the data pack and read in &sect;8 rather than shown here.</em></p>'
            f'{crosslink_html}</section>')


def s8(p, nv):
    ro = p.get("s8_rotation", {})
    def auto_line(d):
        return (f'<li><b>{esc(d.get("index_name",""))}</b> &mdash; '
                f'{signed(d.get("delta"), 0)} pts of participation over five sessions, '
                f'ranked {d.get("rank_1m","&mdash;")} of 14 on the month.</li>')
    in_list  = "".join(f"<li>{t}</li>" for t in nv.get("s8_in",[])) or \
               "".join(auto_line(d) for d in ro.get("ranked_in",[]))
    out_list = "".join(f"<li>{t}</li>" for t in nv.get("s8_out",[])) or \
               "".join(auto_line(d) for d in ro.get("ranked_out",[]))
    impl = f'<div class="callout">{nv.get("s8_implication")}</div>' if nv.get("s8_implication") else ""
    return (f'<section id="s8">{sec_head("8","Sector Rotation")}'
            f'<div class="grid2">'
            f'<div class="card"><h3>Rotating in</h3><ul class="bul">{in_list}</ul></div>'
            f'<div class="card"><h3>Rotating out</h3><ul class="bul">{out_list}</ul></div>'
            f'</div>{impl}</section>')


def scanner_table(rows):
    col = lambda f: [float(f(r)) if f(r) is not None else None for r in rows]
    sh_d1  = shader(col(lambda r: r.get("d1_pct")))
    sh_v14 = shader(col(lambda r: r.get("vol_x14")))
    sh_v63 = shader(col(lambda r: r.get("vol_x63")))
    sh_rsi = shader(col(lambda r: r.get("rsi_14")))
    sh_sma = shader(col(lambda r: r.get("pct_from_sma20")))

    body = "".join(
        f'<tr><td class="sym">{esc(r.get("symbol",""))}</td>'
        f'<td>{esc(r.get("industry",""))}</td>'
        f'<td class="num">{fmt(r.get("ltp"))}</td>'
        f'<td class="num {sh_d1(i)} {cls(r.get("d1_pct"))}">{signed(r.get("d1_pct"))}</td>'
        f'<td class="num {sh_v14(i)}">{fmt(r.get("vol_x14"))}</td>'
        f'<td class="num {sh_v63(i)}">{fmt(r.get("vol_x63"))}</td>'
        f'<td class="num {sh_rsi(i)}">{fmt(r.get("rsi_14"), 1)}</td>'
        f'<td class="num">{fmt(r.get("adx_14"), 1)}</td>'
        f'<td class="num {sh_sma(i)} {cls(r.get("pct_from_sma20"))}">{signed(r.get("pct_from_sma20"), 1)}</td>'
        f'</tr>'
        for i, r in enumerate(rows)
    )
    head = (f'<tr>{thc("Symbol")}{thc("Industry")}{thc("LTP")}{thc("1D %")}'
            f'{thc("Vol<br>&times;14D", True)}{thc("Vol<br>&times;63D", True)}'
            f'{thc("RSI-14", True)}{thc("ADX-14", True)}{thc("% from<br>20SMA", True)}</tr>')
    return make_table(head, body, 760, "compact")


def s9(p, nv):
    sc = p.get("s9_scanners", {})
    gainers = sc.get("gainers", [])
    losers  = sc.get("losers",  [])
    s9_note = f" {nv.get('s9_note')}" if nv.get("s9_note") else ""
    return (f'<section id="s9">{sec_head("9","Stock Scanners")}'
            f'<h3>Strength &mdash; top {len(gainers)} gainers</h3>{scanner_table(gainers)}'
            f'<h3>Weakness &mdash; top {len(losers)} losers</h3>{scanner_table(losers)}'
            f'<p class="cap"><em>Full active universe. <b>RSI-14</b> measures how stretched a move is '
            f'(above 70 is hot, below 30 is washed out). <b>ADX-14</b> measures how strong a trend is, '
            f'regardless of direction &mdash; above 30 is a real trend. '
            f'Two volume multiples: &times;14 catches a fresh spike, &times;63 is the structural baseline.</em>'
            f'{s9_note}</p></section>')


def s10(p, nv):
    m     = p.get("s10_momentum", {})
    fresh = m.get("fresh", [])
    cont  = m.get("continued", [])

    fsh    = shader([float(r["score"]) if r.get("score") is not None else None for r in fresh])
    f_body = "".join(
        f'<tr><td class="num">{r.get("rank","")}</td>'
        f'<td class="sym">{esc(r.get("symbol",""))}</td>'
        f'<td class="num">{fmt(r.get("ltp"))}</td>'
        f'<td class="num {cls(r.get("d1_pct"))}">{signed(r.get("d1_pct"))}</td>'
        f'<td class="num">{fmt(r.get("vol_x14"))}</td>'
        f'<td class="num">{fmt(r.get("vol_x63"))}</td>'
        f'<td class="num {cls(r.get("ret_5d"))}">{signed(r.get("ret_5d"))}</td>'
        f'<td class="num">{"&#10003;" if r.get("trend_3w") else "&#10007;"}</td>'
        f'<td class="num {fsh(i)}">{fmt(r.get("score"), 1)}</td></tr>'
        for i, r in enumerate(fresh)
    )
    c_body = "".join(
        f'<tr><td class="sym">{esc(r.get("symbol",""))}</td>'
        f'<td class="num">{fmt(r.get("ltp"))}</td>'
        f'<td class="num {cls(r.get("d1_pct"))}">{signed(r.get("d1_pct"))}</td>'
        f'<td class="num {cls(r.get("w1_pct"))}">{signed(r.get("w1_pct"))}</td>'
        f'<td class="num">{fmt(r.get("vol_x14"))}</td>'
        f'<td class="num {cls(r.get("pct_from_sma20"))}">{signed(r.get("pct_from_sma20"), 1)}</td>'
        f'<td class="num {cls(r.get("pct_from_sma50"))}">{signed(r.get("pct_from_sma50"), 1)}</td>'
        f'<td class="num">{fmt(r.get("rsi_14"), 1)}</td>'
        f'<td class="num">{fmt(r.get("weekly_rsi"), 1)}</td></tr>'
        for r in cont
    )
    overlap = m.get("overlap", [])
    trigs   = nv.get("s10_triggers", [])
    if trigs:
        trig_block = ('<h3>Possible triggers</h3><ul class="bul narr">'
                      + "".join(f'<li><b>{esc(t.get("symbols",""))}</b> &mdash; {t.get("text","")}</li>' for t in trigs)
                      + '</ul><p class="cap"><em>Only names with a specific, dated catalyst are listed. '
                        'The rest moved without one, which is itself information.</em></p>')
    else:
        trig_block = pending("News triggers", "Web search at report time.")

    f_head = (f'<tr>{th("#", True)}{th("Symbol")}{th("LTP",True)}{th("1D %",True)}'
              f'{th("Vol &times;14",True)}{th("Vol &times;63",True)}{th("5D %",True)}'
              f'{th("3wk",True)}{th("Score",True)}</tr>')
    c_head = (f'<tr>{th("Symbol")}{th("LTP",True)}{th("1D %",True)}{th("1W %",True)}'
              f'{th("Vol &times;14",True)}{th("% from 20SMA",True)}{th("% from 50SMA",True)}'
              f'{th("RSI-14",True)}{th("Weekly RSI",True)}</tr>')

    overlap_block = ""
    if overlap:
        names = ", ".join(esc(n) for n in overlap)
        overlap_block = (f'<div class="callout"><b>In both tables:</b> {names}. '
                         f'A name entering momentum <i>and</i> already in a confirmed trend is a stronger signal than either alone.</div>')

    # Continued momentum context cards from narrative (analyst/order book depth)
    cont_ctx = nv.get("s10_continued_context", [])
    cont_ctx_html = ""
    if cont_ctx:
        cards = "".join(
            f'<div class="card"><h3>{esc(c.get("symbol",""))}</h3>'
            f'<p style="font-size:.85rem">{c.get("context","")}</p></div>'
            for c in cont_ctx
        )
        cont_ctx_html = (f'<h3>Continued momentum &mdash; analyst &amp; order context</h3>'
                         f'<p class="cap"><em>Recent analyst coverage, order book, and corporate events for the continued trend names. '
                         f'Sourced from broker reports, exchange disclosures, and news search at report time.</em></p>'
                         f'<div class="grid3">{cards}</div>')

    return (f'<section id="s10">{sec_head("10","Momentum Composite")}'
            f'<h3>Table 1 &mdash; Fresh Entry</h3>'
            f'{make_table(f_head, f_body, 760)}'
            f'<p class="cap"><em>Filter: daily move &ge; 1.05% and volume &ge; 1.25&times; the 63-day average. '
            f'Scoring: 35% daily move &middot; 25% volume expansion vs the 63-day average &middot; 15% weekly move &middot; '
            f'15% weekly volume expansion &middot; 10% three-week trend. '
            f'The filter is on <b>absolute</b> move, so a faller can rank high &mdash; on volume expansion, not strength.</em></p>'
            f'<h3>Table 2 &mdash; Continued Momentum</h3>'
            f'{make_table(c_head, c_body, 820)}'
            f'<p class="cap"><em>Already in a confirmed trend &mdash; a different question from Table 1, so not scored the same way. '
            f'All of: daily RSI &gt; 60, Supertrend bullish, MACD histogram &gt; 0, ADX &gt; 30, weekly RSI &gt; 40.</em></p>'
            f'{cont_ctx_html}{overlap_block}{trig_block}</section>')


def s11(p, nv):
    f = p.get("s11_flows", {})
    d_body = "".join(
        f'<tr><td class="mono">{esc(d.get("date",""))}</td>'
        f'<td class="num">{fmt(d.get("fii_buy_cr"))}</td>'
        f'<td class="num">{fmt(d.get("fii_sell_cr"))}</td>'
        f'<td class="num {cls(d.get("fii_net_cr"))}">{signed(d.get("fii_net_cr"))}</td>'
        f'<td class="num">{fmt(d.get("dii_buy_cr"))}</td>'
        f'<td class="num">{fmt(d.get("dii_sell_cr"))}</td>'
        f'<td class="num {cls(d.get("dii_net_cr"))}">{signed(d.get("dii_net_cr"))}</td></tr>'
        for d in f.get("daily", [])
    )
    w = f.get("windows", {})
    def w_row(label, o):
        o = o or {}
        return (f'<tr><td>{label}</td>'
                f'<td class="num {cls(o.get("fii_net"))}">{signed(o.get("fii_net"))}</td>'
                f'<td class="num {cls(o.get("dii_net"))}">{signed(o.get("dii_net"))}</td></tr>')
    w_body = "".join([w_row("Today",w.get("today")), w_row("This week",w.get("this_week")),
                      w_row("Last week",w.get("last_week")), w_row("Month to date",w.get("mtd"))])
    rk = f.get("rank", {})
    rank_line = ""
    if rk.get("of_sessions"):
        rank_line = (f'Today\'s FII figure ranks <b>{rk.get("fii_position","?")} of {rk.get("of_sessions","?")}</b> '
                     f'sessions from the most negative; DII ranks <b>{rk.get("dii_position","?")} of {rk.get("of_sessions","?")}</b> from the most negative.')
    absorption = f.get("absorption_pct")
    if rank_line:
        abs_txt = f' Domestic institutions absorbed <b>{fmt(absorption, 0)}%</b> of today\'s foreign selling.' \
                  if absorption is not None else ""
        rank_block = f'<div class="callout gap">{rank_line}{abs_txt}</div>'
    else:
        rank_block = ""

    interp = nv.get("s11_interpretation")
    interp_block = f'<p style="font-size:.9rem">{interp}</p>' if interp else \
                   pending("Flow interpretation", "Written at report time.")

    d_head = (f'<tr>{th("Date")}{th("FII buy",True)}{th("FII sell",True)}{th("FII net",True)}'
              f'{th("DII buy",True)}{th("DII sell",True)}{th("DII net",True)}</tr>')
    w_head = f'<tr>{th("Window")}{th("FII net",True)}{th("DII net",True)}</tr>'

    return (f'<section id="s11">{sec_head("11","FII / DII Flows")}'
            f'{make_table(d_head, d_body, 720)}'
            f'<p class="cap"><em>NSE cash market, &#8377; crore. Last {len(f.get("daily",[]))} sessions.</em></p>'
            f'<h3>Comparison windows</h3>'
            f'{make_table(w_head, w_body, 360)}'
            f'{rank_block}{interp_block}</section>')


def s12(p, nv):
    cards = nv.get("s12_cards", [])
    ch = p.get("s12_changed", {})

    # Auto-generate cards from pack if narrative doesn't supply them
    auto = []
    if ch.get("regime", {}).get("score_delta") is not None:
        auto.append({"title": "Market regime",
                     "lead": f'{signed(ch["regime"]["score_delta"], 1)} points versus the previous session.',
                     "bullets": [f'Now {fmt(p.get("s2_regime",{}).get("score"), 1)} '
                                 f'({esc(p.get("s2_regime",{}).get("band",""))}), '
                                 f'was {fmt(ch["regime"].get("score_prev"), 1)}.']})
    bd = ch.get("breadth", {})
    if bd.get("pct20_today") is not None:
        auto.append({"title": "Participation",
                     "lead": f'{int_(bd.get("pct20_today"))}% of the Nifty 500 sits above its 20-day average.',
                     "bullets": [f'Previous session {int_(bd.get("pct20_prev"))}%.',
                                 f'Advance/decline {fmt(bd.get("ad_today"))} against {fmt(bd.get("ad_prev"))}.']})
    sc = ch.get("sectors", {})
    if sc.get("best_1m"):
        bullets = []
        if sc.get("biggest_5d_gain"):
            bullets.append(f'Fastest participation gain: {esc(sc["biggest_5d_gain"].get("index_name",""))} '
                           f'{signed(sc["biggest_5d_gain"].get("delta"), 0)} pts.')
        auto.append({"title": "Sector extremes",
                     "lead": f'{esc(sc.get("best_1m",""))} leads the month; {esc(sc.get("worst_1m",""))} trails it.',
                     "bullets": bullets})

    all_cards = cards if cards else auto
    cards_html = "".join(
        f'<div class="card"><h3>{esc(c.get("title",""))}</h3>'
        f'<p>{c.get("lead","")}</p>'
        f'<ul class="bul">' + "".join(f"<li>{b}</li>" for b in c.get("bullets",[])) + f"</ul></div>"
        for c in all_cards
    )
    return (f'<section id="s12">{sec_head("12","What Changed Today")}'
            f'<div class="grid3">{cards_html}</div></section>')


def s13(nv):
    a = nv.get("s13")
    if not a:
        return (f'<section id="s13">{sec_head("13","Futures, Options & Expiry")}'
                f'{pending("Futures & Options", "Sourced at report time via Tijori + Web.")}'
                f'</section>')

    # Futures table
    fut_rows = "".join(
        f'<tr><td class="sym">{esc(r.get("instrument",""))}</td>'
        f'<td class="num">{fmt(r.get("close"))}</td>'
        f'<td class="num {cls(r.get("change"))}">{signed(r.get("change"))}</td>'
        f'<td class="num">{int_(r.get("oi"))}</td>'
        f'<td class="num {cls(r.get("oi_change"))}">{signed(r.get("oi_change"), 0)}</td>'
        f'<td class="num">{fmt(r.get("basis"))}</td>'
        f'<td>{esc(r.get("pattern",""))}</td></tr>'
        for r in a.get("futures", [])
    )
    fut_head = (f'<tr>{th("Instrument")}{th("Close",True)}{th("Change",True)}'
                f'{th("OI",True)}{th("OI change",True)}{th("Basis",True)}{th("Pattern")}</tr>')

    # Option chain: strikes left-centre-right layout
    chain_rows = ""
    for r in a.get("chain", []):
        atm_class = " hl" if r.get("atm") else ""
        chain_rows += (f'<tr class="{atm_class.strip()}">'
                       f'<td class="num">{int_(r.get("call_oi"))}</td>'
                       f'<td class="num">{fmt(r.get("ce_close"))}</td>'
                       f'<td class="num" style="font-weight:700;background:var(--navy);color:#EAF1F7">{r.get("strike","")}</td>'
                       f'<td class="num">{int_(r.get("put_oi"))}</td>'
                       f'<td class="num">{fmt(r.get("pe_close"))}</td></tr>')
    chain_head = (f'<tr>{th("CALL OI",True)}{th("CE Close",True)}'
                  f'<th class="ctr" style="background:var(--navy);color:#EAF1F7">STRIKE</th>'
                  f'{th("PUT OI",True)}{th("PE Close",True)}</tr>')

    mt = a.get("metrics", {})
    metrics_block = (
        f'<div class="grid3" style="margin-top:10px">'
        f'<div class="card"><div class="k">Put/Call Ratio</div>'
        f'<div class="v" style="font-size:1.2rem;font-family:IBM Plex Mono,monospace">{fmt(mt.get("pcr"))}</div>'
        f'<p>{mt.get("pcr_note","")}</p></div>'
        f'<div class="card"><div class="k">Max Pain</div>'
        f'<div class="v" style="font-size:1.2rem;font-family:IBM Plex Mono,monospace">{mt.get("max_pain","")}</div>'
        f'<p>{mt.get("max_pain_note","")}</p></div>'
        f'<div class="card"><div class="k">Crossover Strike</div>'
        f'<div class="v" style="font-size:1.2rem;font-family:IBM Plex Mono,monospace">{mt.get("crossover","")}</div>'
        f'<p>{mt.get("crossover_note","")}</p></div>'
        f'</div>'
    )

    struct = f'<div class="callout">{a.get("structural_read","")}</div>' if a.get("structural_read") else ""

    scenarios = a.get("scenarios", [])
    scen_html = ""
    if scenarios:
        scen_html = '<h3>Settlement scenarios</h3><div class="grid3">' + "".join(
            f'<div class="card"><h3>{esc(s.get("name",""))} <span class="pill wn">{esc(s.get("probability",""))}</span></h3>'
            f'<div class="meta">Trigger: {esc(s.get("trigger",""))}</div><p>{s.get("path","")}</p></div>'
            for s in scenarios
        ) + "</div>"

    note_block = f'<div class="callout">{a.get("note","")}</div>' if a.get("note") else ""
    expiry_banner = f'<p class="cap"><em>{esc(a.get("chain_title",""))}</em></p>' if a.get("chain_title") else ""

    return (f'<section id="s13">{sec_head("13","Futures, Options & Expiry")}'
            f'<h3>Index futures</h3>'
            f'{make_table(fut_head, fut_rows, 720)}'
            f'<h3>{esc(a.get("chain_title","Weekly option chain"))}</h3>'
            f'{make_table(chain_head, chain_rows, 400)}'
            f'{expiry_banner}'
            f'{metrics_block}{struct}{scen_html}{note_block}</section>')


def s14(nv):
    a = nv.get("s14")
    if not a:
        return (f'<section id="s14">{sec_head("14","Tomorrow\'s Action Plan")}'
                f'{pending("Action plan","Written at report time. Each item names the signal that would confirm or deny it.")}'
                f'</section>')

    watch = a.get("watch", [])
    watch_html = '<ul class="bul narr">' + "".join(
        f'<li><b>{esc(w.get("item",""))}</b><br>'
        f'Confirms if: {w.get("confirms","")}<br>'
        f'Denies it if: {w.get("denies","")}</li>'
        for w in watch
    ) + "</ul>" if watch else ""

    events = a.get("events", [])
    events_html = (f'<div class="callout"><b>Dated events in the next three sessions.</b> '
                   f'<ul class="bul">{"".join(f"<li>{e}</li>" for e in events)}</ul></div>') if events else ""

    bull = a.get("bull", [])
    bear = a.get("bear", [])
    triggers_html = (f'<div class="grid2">'
                     f'<div class="card"><h3>Bull triggers</h3><ul class="bul">{"".join(f"<li>{b}</li>" for b in bull)}</ul></div>'
                     f'<div class="card"><h3>Bear triggers</h3><ul class="bul">{"".join(f"<li>{b}</li>" for b in bear)}</ul></div>'
                     f'</div>') if (bull or bear) else ""

    closing = f'<div class="callout">{a.get("closing","")}</div>' if a.get("closing") else ""

    return (f'<section id="s14">{sec_head("14","Tomorrow\'s Action Plan")}'
            f'{watch_html}{events_html}{triggers_html}{closing}</section>')


def how_to_read_section():
    cards_html = "".join(
        f'<div class="htr-card">'
        f'<div class="htr-step">Step {h["n"]}</div>'
        f'<h3 class="htr-title">{esc(h["title"])}</h3>'
        f'<p class="htr-body">{h["body"]}</p>'
        f'</div>'
        for h in HOW_TO_READ
    )
    return (
        f'<section id="how-to-read" class="htr-section">'
        f'<div class="htr-badge">GUIDE &amp; METHODOLOGY</div>'
        f'<div class="sec-h"><h2>How to Read This Report</h2></div>'
        f'<div class="htr-lead">The order matters more than the sections. Most readers open at the index level and stop there &mdash; which is the habit that makes a narrow market look healthy.</div>'
        f'<div class="htr-grid">{cards_html}</div>'
        f'</section>'
    )


def quality_section(p):
    q = p.get("quality", {})
    warnings = q.get("warnings", [])
    if not warnings: return ""
    w_items = "".join(f"<li>{esc(w)}</li>" for w in warnings)
    return (f'<section id="notes">{sec_head("&rsaquo;","Data notes")}'
            f'<div class="callout"><b>This edition carries {len(warnings)} data caveat{"s" if len(warnings)>1 else ""}.</b>'
            f'<ul class="bul">{w_items}</ul>'
            f'Coverage {fmt(q.get("coverage_pct"),1)}% &mdash; '
            f'{int_(q.get("daily_prices",{}).get("stocks") if q.get("daily_prices") else None)} stocks and '
            f'{int_(q.get("daily_prices",{}).get("indices") if q.get("daily_prices") else None)} indices priced.'
            f'</div></section>')


# ── HTML assembly ─────────────────────────────────────────────────────────────

# CSS is embedded verbatim from the reference template (brief.html).
# All visual rules come from there — do not change without updating both.
BRIEF_CSS = """\
:root {
  --ground:#F4F6F8; --surface:#FFF; --ink:#1A1E26; --muted:#5A6577;
  --navy:#10263F; --navy-hi:#1B3550; --line:#D4D9E1; --line-2:#EBEEF2;
  --up:#0E7C5A; --dn:#C33A2E; --warn:#8B5E00; --warn-bg:#FFF8E7;
  --chip:#EAEEF1; --zebra:#FAFBFA; --link:#10263F;
  --g1:#BFE3D0; --g2:#D6EDE0; --g3:#E9F5EF;
  --r1:#F6CFC9; --r2:#FAE0DC; --r3:#FDEFED;
  --bar-up:#3E9C77; --bar-dn:#C9705F;
}
/* Light theme only — dark mode override intentionally removed */
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
.expiry{background:var(--warn-bg);color:var(--warn);border:1px solid var(--warn);
  padding:3px 10px;border-radius:3px;font-weight:600;font-size:.75rem;letter-spacing:.02em}
.movement{margin:38px 0 4px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.movement .k{font-family:"IBM Plex Mono",monospace;font-size:.68rem;letter-spacing:.14em;
  text-transform:uppercase;color:var(--warn);font-weight:600}
.movement .t{font-family:"IBM Plex Sans Condensed",sans-serif;font-size:1.05rem;font-weight:700;color:var(--muted)}
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
tr.hl{background:var(--warn-bg)!important}
tr.hl td{font-weight:600}
.bar{position:relative;height:16px;min-width:120px}
.bar .axis{position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--line)}
.bar .fill{position:absolute;top:3px;height:10px;border-radius:1px}
.bar .lbl{position:absolute;top:0;font-family:"IBM Plex Mono",monospace;font-size:.7rem;line-height:16px;color:var(--muted)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:13px}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:13px}
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
.htr-section{margin-top:36px;padding:20px 24px;background:#F8FAFC;border:1px solid #CBD5E1;border-left:5px solid #2563EB;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.03);font-family:"IBM Plex Sans",-apple-system,sans-serif}
.htr-badge{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:.60rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#1E40AF;background:#DBEAFE;padding:2px 8px;border-radius:4px;margin-bottom:6px}
.htr-section h2{font-family:"Georgia","Times New Roman",serif;font-size:1.35rem;font-weight:700;color:#0F172A;margin-top:4px;margin-bottom:12px}
.htr-lead{font-family:"Georgia","Times New Roman",serif;font-size:.88rem;font-style:italic;line-height:1.55;color:#1E293B;background:#FFFFFF;padding:14px 18px;border-radius:6px;border:1px dashed #94A3B8;margin-bottom:18px}
.htr-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.htr-card{background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:12px 14px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}
.htr-step{font-family:"IBM Plex Mono",monospace;font-size:.60rem;font-weight:700;color:#2563EB;text-transform:uppercase;margin-bottom:3px}
.htr-title{font-family:"IBM Plex Sans",sans-serif;font-size:.78rem;font-weight:700;color:#0F172A;margin:0 0 4px 0}
.htr-body{font-family:"IBM Plex Sans",sans-serif;font-size:.68rem;line-height:1.45;color:#334155;margin:0}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media print{
  .no-print{display:none!important}
  nav{display:none!important}
  body{background:#FFF!important;color:#111!important}
  .mast{background:#10263F!important}
  .twrap{overflow:visible!important;border-color:#CCC}
  table{min-width:0!important;font-size:.72rem}
  thead th{background:#10263F!important;color:#FFF!important;position:static!important}
  tbody tr,.card,.callout,.tile{break-inside:avoid;page-break-inside:avoid}
  section{break-inside:auto}
  .sec-h{break-after:avoid}
}
"""

# Google Fonts preconnect + face declarations
FONTS_HTML = """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">"""

MOVEMENTS = [
    {"key": "A", "title": "The Read",         "ids": ["s1","s2","s3"]},
    {"key": "B", "title": "The Context",       "ids": ["s4","s5"]},
    {"key": "C", "title": "The Structure",     "ids": ["s6","s7","s8","s9","s10","s11"]},
    {"key": "D", "title": "The Forward View",  "ids": ["s12","s13","s14","how-to-read"]},
]
LABELS = {
    "s1":"\u00a71 Scorecard","s2":"\u00a72 Regime","s3":"\u00a73 Unusual",
    "s4":"\u00a74 Macro","s5":"\u00a75 Global","s6":"\u00a76 Structure",
    "s7":"\u00a77 Breadth","s8":"\u00a78 Rotation","s9":"\u00a79 Scanners",
    "s10":"\u00a710 Momentum","s11":"\u00a711 Flows",
    "s12":"\u00a712 Changed","s13":"\u00a713 F&O","s14":"\u00a714 Plan",
    "how-to-read":"How to Read",
}

SORT_JS = r"""
(function(){
  document.querySelectorAll("table").forEach(function(t){
    var hs=t.querySelectorAll("thead th[data-s]");
    hs.forEach(function(h,idx){
      h.addEventListener("click",function(){
        var tb=t.querySelector("tbody"); if(!tb) return;
        var asc=!h.classList.contains("asc");
        hs.forEach(function(o){o.classList.remove("asc","desc");});
        h.classList.add(asc?"asc":"desc");
        var rows=Array.prototype.slice.call(tb.querySelectorAll("tr"));
        rows.sort(function(a,b){
          var x=a.children[idx],y=b.children[idx]; if(!x||!y) return 0;
          var xt=x.textContent.trim(),yt=y.textContent.trim();
          var xn=parseFloat(xt.replace(/[^0-9.\-]/g,"")),yn=parseFloat(yt.replace(/[^0-9.\-]/g,""));
          if(!isNaN(xn)&&!isNaN(yn)) return asc?xn-yn:yn-xn;
          return asc?xt.localeCompare(yt):yt.localeCompare(xt);
        });
        rows.forEach(function(r){tb.appendChild(r);});
      });
    });
  });
"""

SCROLL_SPY_JS_TPL = r"""
  var ids=NAV_IDS_PLACEHOLDER;
  var links={};
  ids.forEach(function(id){var a=document.querySelector('nav a[href="#'+id+'"]');if(a) links[id]=a;});
  function spy(){
    var best=null,bestTop=-Infinity;
    ids.forEach(function(id){
      var el=document.getElementById(id); if(!el) return;
      var top=el.getBoundingClientRect().top-60;
      if(top<=0&&top>bestTop){bestTop=top;best=id;}
    });
    ids.forEach(function(id){if(links[id]) links[id].classList.remove("on");});
    if(best&&links[best]) links[best].classList.add("on");
  }
  window.addEventListener("scroll",spy,{passive:true});
  spy();
})();
"""

STUB = {
    "headline": "", "standfirst": "",
    "s1_bullets": [{"emoji": "??", "label": "Global", "text": ""}],
    "s1_commodities": [{"name": "Brent crude", "value": "$0.00", "change": "0.00%", "dir": "down"}],
    "s2_glosses": {"Breadth":"","Trend":"","Momentum":"","InstitutionalFlow":"","Volatility":""},
    "s2_composition_note": "",
    "s3_anomalies": [],
    "s4_macro_cards": [{"title":"","pill":"","pill_class":"wn","meta":"","bullets":[""]}],
    "s5_global": [{"instrument":"","level":"","change":"","dir":"down","signal":""}],
    "s5_timing_note": "", "s6_note": "", "s7_note": "", "s9_note": "",
    "s8_in": [""], "s8_out": [""], "s8_implication": "",
    "s10_triggers": [{"symbols":"","text":""}],
    "s11_interpretation": "",
    "s12_cards": [{"title":"","lead":"","bullets":[""]}],
    "s13": None,
    "s14": {"watch":[{"item":"","confirms":"","denies":""}],"events":[""],"bull":[""],"bear":[""],"closing":""},
}


# ── main ───────────────────────────────────────────────────────────────────────

def render(pack_date, pack, nv, has_narr):
    """Build the full HTML string from pack + narrative."""
    # Nav and section structure
    nav_ids = [id_ for mv in MOVEMENTS for id_ in mv["ids"]]
    nav_html = "".join(
        f'<span class="mv">{mv["key"]}</span>'
        + "".join(f'<a href="#{id_}">{LABELS[id_]}</a>' for id_ in mv["ids"])
        for mv in MOVEMENTS
    )

    # Auto-load Tijori Macro Summary if available
    macro_summary_path = os.path.join(ROOT, "data", "macro", f"macro_summary_{pack_date}.json")
    if os.path.exists(macro_summary_path):
        try:
            with open(macro_summary_path, encoding="utf-8") as f:
                macro_sum = json.load(f)
            
            # Populate metals for §1 if missing
            if not nv.get("s1_metals") and macro_sum.get("metals"):
                m_list = []
                for m in macro_sum.get("metals", []):
                    chg_1w = m.get("change_1w") or "0%"
                    dir_str = "up" if chg_1w.startswith("+") or (not chg_1w.startswith("-") and chg_1w != "0%") else ("down" if chg_1w.startswith("-") else "flat")
                    m_list.append({
                        "name": m.get("name"),
                        "value": f"1W: {chg_1w}",
                        "change": f"1M: {m.get('change_1m') or '&mdash;'}",
                        "dir": dir_str
                    })
                nv["s1_metals"] = m_list
                nv["s1_metals_source"] = "Tijori Raw Materials Feed"

            # Populate §4 Macro Cards if missing
            if not nv.get("s4_macro_cards") and macro_sum.get("indicators"):
                ind_map = macro_sum.get("indicators", {})
                cards = []
                # Group key indicators into cards
                gst = ind_map.get("gst_collection") or ind_map.get("gst_collection____(crores)")
                if gst:
                    cards.append({
                        "title": "GST Collections & Demand",
                        "pill": f"Latest: {gst.get('value')} Cr",
                        "pill_class": "up",
                        "meta": f"Tijori Demand Feed ({gst.get('latest_period','-')})",
                        "bullets": [
                            f"Gross GST Collections recorded at <b>{gst.get('value')} Cr</b> for {gst.get('latest_period')}.",
                            "Personal loans outstanding and credit card momentum continue to track domestic consumption health."
                        ]
                    })
                if cards:
                    nv["s4_macro_cards"] = cards
        except Exception as e:
            print(f"Warning: Failed to load macro summary for rendering: {e}")

    # Auto-load Tijori Stock Enrichment if available
    enrich_path = os.path.join(ROOT, "data", "enrichment", f"momentum_enriched_{pack_date}.json")
    if os.path.exists(enrich_path):
        try:
            with open(enrich_path, encoding="utf-8") as f:
                enrich_data = json.load(f)
            stocks_intel = enrich_data.get("stocks", {})
            if stocks_intel and not nv.get("s10_triggers"):
                trigs = []
                for sym, info in stocks_intel.items():
                    ov = info.get("overview", {})
                    kb = info.get("knowledge_base", {})
                    op = info.get("operational_metrics", {})
                    desc = ov.get("business_summary") or kb.get("summary") or ""
                    if desc:
                        # Extract first sentence for quick trigger bullet
                        short_desc = desc.split(". ")[0] + "."
                        trigs.append({"symbols": sym, "text": f"{short_desc} (Source: Tijori)"})
                    if len(trigs) >= 10:
                        break
                if trigs:
                    nv["s10_triggers"] = trigs
        except Exception as e:
            print(f"Warning: Failed to load momentum enrichment for rendering: {e}")

    # Sections
    sections_html = ""
    for mv in MOVEMENTS:
        sections_html += f'<div class="movement"><div class="k">{mv["key"]} &middot; {esc(mv["title"])}</div></div>'
        for id_ in mv["ids"]:
            if   id_ == "s1":  sections_html += s1(pack, nv)
            elif id_ == "s2":  sections_html += s2(pack, nv)
            elif id_ == "s3":  sections_html += s3(pack, nv)
            elif id_ == "s4":  sections_html += s4(nv)
            elif id_ == "s5":  sections_html += s5(nv)
            elif id_ == "s6":  sections_html += s6(pack, nv)
            elif id_ == "s7":  sections_html += s7(pack, nv)
            elif id_ == "s8":  sections_html += s8(pack, nv)
            elif id_ == "s9":  sections_html += s9(pack, nv)
            elif id_ == "s10": sections_html += s10(pack, nv)
            elif id_ == "s11": sections_html += s11(pack, nv)
            elif id_ == "s12": sections_html += s12(pack, nv)
            elif id_ == "s13": sections_html += s13(nv)
            elif id_ == "s14": sections_html += s14(nv)
            elif id_ == "how-to-read": sections_html += how_to_read_section()
    sections_html += quality_section(pack)

    # Pretty date
    try:
        dt = datetime.fromisoformat(pack_date + "T00:00:00+05:30")
        pretty_date = dt.strftime("%A, %-d %B %Y") if os.name != "nt" else dt.strftime("%A, %#d %B %Y")
        short_date  = dt.strftime("%-d %b")         if os.name != "nt" else dt.strftime("%#d %b")
    except:
        pretty_date = pack_date
        short_date  = pack_date

    q = pack.get("quality", {})
    headline   = esc(nv.get("headline")  or "NIFTY & BEYOND")
    standfirst = esc(nv.get("standfirst") or f"What the index doesn\u2019t tell you \u2003 NSE \u2003 {pretty_date}")
    title_tag  = esc(f"Nifty & Beyond \u2014 {short_date}")
    topbar     = esc(f"{pack_date} \u2014 close 15:30 IST \u2014 Supabase pack v{pack.get('pack_version','?')}"
                     + (" + Tijori + web" if has_narr else " \u2014 data-only edition"))

    expiry_banner = ""
    s13_nv = nv.get("s13") or {}
    if s13_nv.get("expiry_banner"):
        expiry_banner = f'<span class="expiry">{esc(s13_nv["expiry_banner"])}</span>'

    scroll_js = SCROLL_SPY_JS_TPL.replace("NAV_IDS_PLACEHOLDER", json.dumps(nav_ids))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_tag}</title>
<meta name="description" content="NSE post-market brief: breadth, rotation, flows and F&amp;O analysis for {pretty_date}.">
{FONTS_HTML}
<style>
{BRIEF_CSS}
</style>
</head>
<body>

<div class="mast"><div class="wrap">
  <div>
    <h1>{headline}</h1>
    <div class="sub">{standfirst}</div>
  </div>
  <button class="pdfbtn no-print" onclick="window.print()">Download as PDF</button>
</div></div>

<nav class="no-print"><div class="wrap">{nav_html}</div></nav>

<div class="topbar"><div class="wrap">
  <span class="mono">{topbar}</span>
  {expiry_banner}
</div></div>

<div class="wrap">
{sections_html}
</div>

<script>
{SORT_JS}
{scroll_js}
</script>

</body>
</html>"""
    return html


def verify_html(html, pack_date):
    """Quick sanity checks on rendered HTML. Returns (passed, report_lines)."""
    lines = []
    ok = True

    # Tag balance (open vs close for key tags)
    for tag in ["section", "table", "tbody", "thead", "div", "ul"]:
        opens  = len(re.findall(f"<{tag}[\\s>]", html, re.I))
        closes = len(re.findall(f"</{tag}>",     html, re.I))
        if opens != closes:
            lines.append(f"  FAIL tag mismatch <{tag}>: {opens} open, {closes} close")
            ok = False
    lines.append(f"  OK  tag balance checked")

    # No raw __ placeholders remaining
    placeholders = re.findall(r"__[A-Z_]+__", html)
    if placeholders:
        lines.append(f"  FAIL unreplaced placeholders: {set(placeholders)}")
        ok = False
    else:
        lines.append(f"  OK  no unreplaced placeholders")

    # Count pending blocks (data-only sections)
    pending_count = html.count('class="pending"')
    lines.append(f"  INFO pending blocks: {pending_count}"
                 + (" (data-only edition)" if pending_count > 3 else ""))

    # Count section elements
    section_count = len(re.findall(r'<section id="s\d+"', html))
    lines.append(f"  INFO sections rendered: {section_count} (expected 14)")
    if section_count != 14:
        lines.append(f"  WARN section count is {section_count}, expected 14")
        ok = False

    # File size
    size_kb = len(html.encode("utf-8")) / 1024
    lines.append(f"  INFO size: {size_kb:.1f} KB")
    if size_kb < 20:
        lines.append(f"  WARN very small — is pack data populated?")

    return ok, lines


def write_stub(pack_date, pack, narr_path):
    """Write a narrative skeleton for filling."""
    # s3: must have exactly len(candidates) entries
    candidates = (pack.get("s3_unusual") or {}).get("candidates", [])
    stub = dict(STUB)
    stub["report_date"] = pack_date
    stub["s3_anomalies"] = [{"title": "", "text": ""} for _ in candidates]
    with open(narr_path, "w", encoding="utf-8") as f:
        json.dump(stub, f, ensure_ascii=False, indent=2)
    print(f"  Narrative stub written: {narr_path}")
    print(f"  s3_anomalies has {len(candidates)} slot(s) -- one per unusual candidate in the pack.")
    print(f"  Fill all keys, then re-run without --stub.")


def main():
    args = sys.argv[1:]
    date_arg  = next((a for a in args if re.match(r"\d{4}-\d{2}-\d{2}$", a)), None)
    do_stub   = "--stub"   in args
    do_verify = "--verify" in args

    # Resolve pack
    os.makedirs(PACK_DIR,  exist_ok=True)
    os.makedirs(NARR_DIR,  exist_ok=True)
    os.makedirs(OUT_DIR,   exist_ok=True)

    if date_arg:
        pack_path = os.path.join(PACK_DIR, f"{date_arg}.json")
        if not os.path.exists(pack_path):
            print(f"ERROR: Pack not found: {pack_path}")
            print(f"       Run: python scripts/fetch_pack.py {date_arg}")
            sys.exit(1)
    else:
        # Use latest cached pack
        cached = sorted(f for f in os.listdir(PACK_DIR) if f.endswith(".json"))
        if not cached:
            print("ERROR: No cached packs. Run: python scripts/fetch_pack.py")
            sys.exit(1)
        pack_path = os.path.join(PACK_DIR, cached[-1])
        date_arg  = cached[-1].replace(".json","")
        print(f"  Using latest cached pack: {date_arg}")

    with open(pack_path, encoding="utf-8") as f:
        pack = json.load(f)

    narr_path = os.path.join(NARR_DIR, f"{date_arg}.json")

    if do_stub:
        write_stub(date_arg, pack, narr_path)
        return

    nv = {}
    has_narr = False
    if os.path.exists(narr_path):
        with open(narr_path, encoding="utf-8") as f:
            nv = json.load(f)
        has_narr = bool(nv)

    html = render(date_arg, pack, nv, has_narr)

    out_filename = f"{date_arg}-daily-brief.html"
    out_path = os.path.join(OUT_DIR, out_filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    kb = len(html.encode("utf-8")) / 1024
    q  = pack.get("quality", {})
    print(f"\n{'='*58}")
    print(f"Rendered {out_path}")
    print(f"{'='*58}")
    print(f"  mode        {'full (narrative found)' if has_narr else 'DATA-ONLY (no narrative file)'}")
    print(f"  pack        {date_arg}  v{pack.get('pack_version','?')}  coverage {q.get('coverage_pct','?')}%")
    print(f"  size        {kb:.1f} KB")
    print(f"  sections    14 across 4 movements")
    warnings = q.get("warnings", [])
    if warnings:
        print(f"\n  {len(warnings)} data caveat(s) disclosed in the report.")
    if not has_narr:
        print(f"\n  To author prose: python scripts/render_report.py {date_arg} --stub")

    if do_verify:
        print(f"\n--- VERIFY ---")
        ok, vlines = verify_html(html, date_arg)
        for l in vlines: print(l)
        print(f"--- {'PASS' if ok else 'FAIL'} ---\n")
        if not ok: sys.exit(1)

    print(f"\n  Rename for publishing: {date_arg.replace('-','')+'.html'}\n")

if __name__ == "__main__":
    main()
