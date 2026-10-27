"""
Turns a weekly snapshot (see weekly.py) into comparisons, ranked
opportunities, experiment evaluations and the dated markdown report.

Every number in the report comes from the snapshot. Where a figure is an
estimate (e.g. "clicks if this ranked 3rd") it is labelled as such, and
period changes carry a noise check so normal fluctuation isn't read as a trend.
"""
import datetime as dt
import math
import os
import re
import subprocess
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import json as _json
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"), encoding="utf-8") as _f:
    _CFG = _json.load(_f)
SITE = _CFG["site_origin"]
DOMAIN = _CFG["domain"]  # bare domain, e.g. aspirantdaily.com


# ---------------------------------------------------------------- helpers

def d(s):
    return dt.date.fromisoformat(s[:10])


def agg(rows):
    c = sum(r["clicks"] for r in rows)
    i = sum(r["impressions"] for r in rows)
    pos = sum(r["position"] * r["impressions"] for r in rows) / i if i else None
    return {"clicks": c, "impressions": i, "ctr": c / i if i else 0, "position": pos}


def in_window(rows, win, key="date"):
    s, e = d(win[0]), d(win[1])
    return [r for r in rows if s <= d(r[key]) <= e]


def pct(new, old):
    if not old:
        return None
    return (new - old) / old


def fmt_pct(x, plus=True):
    if x is None:
        return "n/a"
    return f"{x:+.0%}" if plus else f"{x:.1%}"


def fmt_n(x, nd=0):
    if x is None:
        return "n/a"
    return f"{x:,.{nd}f}"


def poisson_z(new, old):
    """Rough z for a change in two counts. Fine for clicks; overstates
    confidence for impressions, which vary more than Poisson day to day."""
    if new + old == 0:
        return 0.0
    return (new - old) / math.sqrt(new + old)


def welch_t(a, b):
    """t statistic comparing the daily values of two windows."""
    if len(a) < 2 or len(b) < 2:
        return 0.0
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    return (ma - mb) / se if se else 0.0


def signal(z):
    z = abs(z)
    if z >= 3:
        return "clear change"
    if z >= 2:
        return "likely real"
    if z >= 1:
        return "possible, not conclusive"
    return "within normal fluctuation"


def expected_ctr(pos, cfg):
    table = sorted((float(k), v) for k, v in cfg["ctr_assumption_by_position"].items())
    if pos is None:
        return 0
    if pos <= table[0][0]:
        return table[0][1]
    for (p0, c0), (p1, c1) in zip(table, table[1:]):
        if p0 <= pos <= p1:
            return c0 + (c1 - c0) * (pos - p0) / (p1 - p0)
    return table[-1][1]


def norm_url(u):
    return u.split("#")[0]


def path_of(u):
    return re.sub(r"^https?://[^/]+", "", norm_url(u)) or "/"


def section_of(u):
    p = path_of(u).strip("/").split("/")
    if len(p) >= 2 and p[0] in ("learn", "study"):
        return f"/{p[0]}/{p[1]}/"
    return f"/{p[0]}/" if len(p) > 1 else "/ (root pages)"


def merge_pages(rows):
    """Collapse #fragment variants Search Console reports separately."""
    out = {}
    for r in rows:
        k = norm_url(r["page"]) if "page" in r else None
        if k is None:
            continue
        if k in out:
            o = out[k]
            tot = o["impressions"] + r["impressions"]
            o["position"] = ((o["position"] * o["impressions"] + r["position"] * r["impressions"]) / tot
                             if tot else o["position"])
            o["clicks"] += r["clicks"]
            o["impressions"] = tot
            o["ctr"] = o["clicks"] / tot if tot else 0
        else:
            out[k] = dict(r, page=k)
    return list(out.values())


# ---------------------------------------------------------------- analysis

def gsc_periods(snap):
    daily = snap["gsc"]["daily"]
    win = snap["windows"]
    res = {}
    for k in ("cur7", "prev7", "cur28", "prev28", "yoy28"):
        rows = in_window(daily, win[k])
        res[k] = dict(agg(rows), days=len(rows), daily_clicks=[r["clicks"] for r in rows],
                      daily_impr=[r["impressions"] for r in rows])
    cmps = []
    for cur, prev, label in (("cur7", "prev7", "Last 7 days vs previous 7"),
                             ("cur28", "prev28", "Last 28 days vs previous 28"),
                             ("cur28", "yoy28", "Last 28 days vs same 28 days last year")):
        a, b = res[cur], res[prev]
        if b["days"] < 0.7 * (7 if cur == "cur7" else 28):
            cmps.append({"label": label, "unavailable": f"only {b['days']} days of data in comparison period"})
            continue
        if b["impressions"] < 0.1 * a["impressions"]:
            cmps.append({"label": label, "unavailable": f"site had almost no search presence then "
                                                        f"({fmt_n(b['impressions'])} impressions) — not comparable"})
            continue
        cmps.append({
            "label": label,
            "clicks": (a["clicks"], b["clicks"], pct(a["clicks"], b["clicks"]),
                       signal(welch_t(a["daily_clicks"], b["daily_clicks"]))),
            "impressions": (a["impressions"], b["impressions"], pct(a["impressions"], b["impressions"]),
                            signal(welch_t(a["daily_impr"], b["daily_impr"]))),
            "ctr": (a["ctr"], b["ctr"]),
            "position": (a["position"], b["position"]),
        })
    return res, cmps


def compare_rows(cur, prev, key):
    p = {r[key]: r for r in prev}
    out = []
    for r in cur:
        o = p.get(r[key], {"clicks": 0, "impressions": 0, "ctr": 0, "position": None})
        out.append({key: r[key], "c1": r["clicks"], "c0": o["clicks"], "i1": r["impressions"],
                    "i0": o["impressions"], "pos1": r["position"], "pos0": o["position"],
                    "ctr1": r["ctr"], "z_c": poisson_z(r["clicks"], o["clicks"]),
                    "z_i": poisson_z(r["impressions"], o["impressions"])})
    seen = {r[key] for r in cur}
    for k, o in p.items():
        if k not in seen:
            out.append({key: k, "c1": 0, "c0": o["clicks"], "i1": 0, "i0": o["impressions"],
                        "pos1": None, "pos0": o["position"], "ctr1": 0,
                        "z_c": poisson_z(0, o["clicks"]), "z_i": poisson_z(0, o["impressions"])})
    return out


def analyze(snap, cfg, sitemap, experiments=()):
    r = {"notes": []}
    g = snap.get("gsc")
    export = snap["meta"]["source"] == "export"
    if g:
        r["periods"], r["comparisons"] = gsc_periods(snap)
        pkey = "export" if export else "cur28"
        pages = merge_pages(g["pages"][pkey])
        queries = g["queries"][pkey]
        r["top_pages"] = sorted(pages, key=lambda x: (-x["clicks"], -x["impressions"]))[:10]
        if not export:
            cmp_p = compare_rows(pages, merge_pages(g["pages"]["prev28"]), "page")
            r["page_cmp"] = {x["page"]: x for x in cmp_p}
            r["declining"] = sorted(
                [x for x in cmp_p if (x["c1"] < x["c0"] and x["z_c"] <= -2)
                 or (x["i0"] >= 100 and pct(x["i1"], x["i0"]) <= -0.3 and x["z_i"] <= -3)],
                key=lambda x: (x["c1"] - x["c0"], x["i1"] - x["i0"]))[:10]
            cmp_q = compare_rows(queries, g["queries"]["prev28"], "query")
            r["rising_queries"] = sorted([x for x in cmp_q if x["i1"] >= 50 and x["z_i"] >= 3],
                                         key=lambda x: -(x["i1"] - x["i0"]))[:15]
        # near-first-page and low-CTR opportunities
        rows = (merge_pages_query(g["page_query"]["cur28"]) if g.get("page_query")
                else [dict(q, page=None) for q in queries])
        striking, low_ctr = [], []
        for x in rows:
            pos, imp = x["position"], x["impressions"]
            if 4 <= pos <= 20 and imp >= 50:
                x = dict(x, upside=imp * max(0, expected_ctr(3, cfg) - x["ctr"]))
                striking.append(x)
        for p in pages:
            if p["impressions"] >= 200 and p["position"] <= 15 and p["ctr"] < 0.5 * expected_ctr(p["position"], cfg):
                low_ctr.append(dict(p, upside=p["impressions"] * (expected_ctr(p["position"], cfg) - p["ctr"])))
        r["striking_queries"] = sorted(striking, key=lambda x: -x["upside"])[:25]
        r["low_ctr_pages"] = sorted(low_ctr, key=lambda x: -x["upside"])[:15]
        by_page = defaultdict(lambda: {"upside": 0, "impressions": 0, "queries": []})
        for x in striking:
            if x.get("page"):
                b = by_page[x["page"]]
                b["upside"] += x["upside"]
                b["impressions"] += x["impressions"]
                b["queries"].append(x)
        r["striking_pages"] = sorted(({"page": k, **v} for k, v in by_page.items()),
                                     key=lambda x: -x["upside"])[:15]
        # demand where nothing ranks well yet: evidence for improving or adding content
        best_pos = defaultdict(lambda: 999)
        for x in rows:
            best_pos[x["query"]] = min(best_pos[x["query"]], x["position"])
        r["content_gaps"] = sorted([q for q in queries if q["impressions"] >= 30 and best_pos[q["query"]] > 20],
                                   key=lambda x: -x["impressions"])[:15]
        # several pages splitting one query
        if g.get("page_query"):
            pq = defaultdict(list)
            for x in merge_pages_query(g["page_query"]["cur28"]):
                pq[x["query"]].append(x)
            cann = []
            for q, lst in pq.items():
                tot = sum(x["impressions"] for x in lst)
                big = [x for x in lst if x["impressions"] >= 0.2 * tot]
                if tot >= 50 and len(big) >= 2:
                    cann.append({"query": q, "impressions": tot, "pages": sorted(big, key=lambda x: -x["impressions"])})
            r["cannibal"] = sorted(cann, key=lambda x: -x["impressions"])[:10]
        # sitemap URLs that got no impressions at all
        seen = {p["page"] for p in pages}
        unseen = [u for u in sitemap if u not in seen]
        sec = defaultdict(lambda: [0, 0])
        for u in sitemap:
            sec[section_of(u)][1] += 1
        for u in unseen:
            sec[section_of(u)][0] += 1
        r["unseen"] = {"count": len(unseen), "total": len(sitemap),
                       "by_section": sorted(((k, v[0], v[1]) for k, v in sec.items() if v[0]), key=lambda x: -x[1])}
        ckey = "export" if export else "cur28"
        r["countries"] = sorted(g["countries"][ckey], key=lambda x: -x["impressions"])[:10]
        r["devices"] = g["devices"][ckey]
        if not export:
            pc = {x["country"]: x for x in g["countries"]["prev28"]}
            for c in r["countries"]:
                c["prev_clicks"] = pc.get(c["country"], {}).get("clicks", 0)
        r["inspections"] = g.get("inspections")
        r["sitemaps"] = g.get("sitemaps")
    r["ga4"] = analyze_ga4(snap, cfg) if snap.get("ga4") else None
    r["adsense"] = analyze_adsense(snap) if snap.get("adsense") else None
    r["bing"] = analyze_bing(snap) if snap.get("bing") else None
    # "holds_back": false = a performance-only change (e.g. image caching) whose pages may still get
    # content or snippet work; otherwise a site-wide experiment would freeze every page for a month
    running = [(e["id"], re.compile(e["pages_regex"])) for e in experiments
               if e.get("status") == "running" and e.get("holds_back", True)]
    r["opportunities"], r["held_back"] = rank_opportunities(r, cfg, running)
    return r


def merge_pages_query(rows):
    out = {}
    for x in rows:
        k = (norm_url(x["page"]), x["query"])
        if k in out:
            o = out[k]
            tot = o["impressions"] + x["impressions"]
            o["position"] = (o["position"] * o["impressions"] + x["position"] * x["impressions"]) / tot if tot else o["position"]
            o["clicks"] += x["clicks"]
            o["impressions"] = tot
            o["ctr"] = o["clicks"] / tot if tot else 0
        else:
            out[k] = dict(x, page=k[0])
    return list(out.values())


def analyze_ga4(snap, cfg):
    a = snap["ga4"]
    res = {"property": a["property"], "windows": {}}
    for k, rows in a["totals"].items():
        org = [x for x in rows if x["sessionDefaultChannelGroup"] == "Organic Search"]
        res["windows"][k] = {
            "users_all": sum(x["totalUsers"] for x in rows),
            "sessions_all": sum(x["sessions"] for x in rows),
            "users_organic": sum(x["totalUsers"] for x in org),
            "sessions_organic": sum(x["sessions"] for x in org),
            "engaged_organic": sum(x["engagedSessions"] for x in org),
            "views_all": sum(x["screenPageViews"] for x in rows),
            "channels": sorted(rows, key=lambda x: -x["sessions"]),
        }
    daily = defaultdict(float)
    for x in a["daily_channels"]:
        if x["sessionDefaultChannelGroup"] == "Organic Search":
            daily[x["date"]] += x["totalUsers"]
    win = snap["windows"]

    def avg_daily(k):
        s, e = d(win[k][0]), d(win[k][1])
        days = (e - s).days + 1
        vals = [daily.get((s + dt.timedelta(i)).strftime("%Y%m%d"), 0) for i in range(days)]
        return sum(vals) / days, vals
    res["organic_users_per_day"] = {k: avg_daily(k)[0] for k in ("cur7", "prev7", "cur28", "prev28")}
    res["organic_trend_signal"] = signal(welch_t(avg_daily("cur28")[1], avg_daily("prev28")[1]))
    res["goal"] = cfg["goal_organic_users_per_day"]
    lp = a["landing_organic"]["cur28"]
    tot_s = sum(x["sessions"] for x in lp)
    avg_er = sum(x["engagedSessions"] for x in lp) / tot_s if tot_s else 0
    res["landing_top"] = lp[:10]
    res["landing_avg_er"] = avg_er
    # "(not set)" = sessions GA4 couldn't tie to a page_view, not a real landing page
    res["low_engagement"] = [x for x in lp if x["sessions"] >= 20 and x["engagementRate"] < avg_er - 0.15
                             and x["landingPage"] != "(not set)"][:10]
    res["countries"] = a.get("countries_organic", [])[:10]
    res["devices"] = a.get("devices_organic", [])
    res["organic_sources"] = a.get("organic_sources", [])
    # cities sending many sessions with ~0% engagement are almost always bots / data centres
    res["likely_bots"] = [x for x in a.get("city_channel", [])
                          if x["sessions"] >= 30 and x["engagementRate"] < 0.03]
    pages = a.get("ad_pages") or []
    rev = sum(x["totalAdRevenue"] for x in pages)
    if rev > 0:
        for x in pages:
            x["rpm"] = x["totalAdRevenue"] / x["screenPageViews"] * 1000 if x["screenPageViews"] else 0
        res["ad_pages"] = sorted(pages, key=lambda x: -x["totalAdRevenue"])[:10]
        site_rpm = rev / sum(x["screenPageViews"] for x in pages) * 1000
        res["site_rpm_ga4"] = site_rpm
        res["low_rpm_pages"] = sorted([x for x in pages if x["screenPageViews"] >= 200 and x["rpm"] < 0.5 * site_rpm],
                                      key=lambda x: -x["screenPageViews"])[:10]
    else:
        res["ad_pages_note"] = a.get("ad_pages_error") or (
            "GA4 reports no ad revenue by page -- AdSense is probably not linked to this GA4 property "
            "(Admin > Product links > AdSense). Page-level RPM is unavailable until it is.")
    return res


def analyze_adsense(snap):
    a = snap["adsense"]
    rows = a["daily"]
    others = defaultdict(lambda: [0.0, 0.0])
    if rows and "DOMAIN_NAME" in rows[0]:
        for x in rows:
            dom = x["DOMAIN_NAME"] or ""
            if DOMAIN in dom:
                continue
            # one Vercel preview URL per deployment -- group them
            key = "Vercel preview deployments (*.vercel.app)" if dom.endswith(".vercel.app") else dom
            others[key][0] += x["ESTIMATED_EARNINGS"]
            others[key][1] += x["PAGE_VIEWS"]
        rows = [x for x in rows if DOMAIN in (x["DOMAIN_NAME"] or "")]
    win = snap["windows"]
    res = {"account": a["account"], "other_domains": sorted(others.items(), key=lambda kv: -kv[1][1]),
           "windows": {}, "currency": next((x["currency"] for x in rows if x.get("currency")), "")}
    for k in ("cur7", "prev7", "cur28", "prev28"):
        w = in_window(rows, win[k], key="DATE")
        e = sum(x["ESTIMATED_EARNINGS"] for x in w)
        pv = sum(x["PAGE_VIEWS"] for x in w)
        res["windows"][k] = {"earnings": e, "page_views": pv, "impressions": sum(x["IMPRESSIONS"] for x in w),
                             "clicks": sum(x["CLICKS"] for x in w), "rpm": e / pv * 1000 if pv else 0,
                             "daily": [x["ESTIMATED_EARNINGS"] for x in w]}
    res["signal28"] = signal(welch_t(res["windows"]["cur28"]["daily"], res["windows"]["prev28"]["daily"]))
    res["countries"] = sorted(a.get("countries", []), key=lambda x: -x["ESTIMATED_EARNINGS"])[:10]
    return res


def analyze_bing(snap):
    b = snap["bing"]
    win = snap["windows"]
    res = {"site": b["site"], "windows": {}}
    traffic = [x for x in b["traffic"] if x["date"]]
    for k in ("cur7", "prev7", "cur28", "prev28"):
        w = in_window(traffic, win[k])
        res["windows"][k] = dict(clicks=sum(x["clicks"] for x in w), impressions=sum(x["impressions"] for x in w),
                                 days=len(w), daily=[x["clicks"] for x in w])
    res["signal28"] = signal(welch_t(res["windows"]["cur28"]["daily"], res["windows"]["prev28"]["daily"]))

    # query/page stats are weekly buckets: take the buckets dated inside the last 28 days (+6 so the
    # bucket containing the window start counts)
    s = (d(win["cur28"][0]) - dt.timedelta(days=6)).isoformat()
    e = win["cur28"][1]

    def top(rows, key, start=s):
        acc = defaultdict(lambda: {"clicks": 0, "impressions": 0, "_pos": 0.0})
        for x in rows:
            if not x["date"] or not (start <= x["date"] <= e):
                continue
            a = acc[x[key]]
            a["clicks"] += x["clicks"]
            a["impressions"] += x["impressions"]
            a["_pos"] += (x["avg_impression_position"] or 0) * x["impressions"]
        out = [{key: k, "clicks": v["clicks"], "impressions": v["impressions"],
                "position": v["_pos"] / v["impressions"] if v["impressions"] else None} for k, v in acc.items()]
        return sorted(out, key=lambda x: (-x["clicks"], -x["impressions"]))
    res["queries"] = top(b["queries"], "query")
    res["pages"] = top(b["pages"], "page")
    res["crawl_latest"] = max(b.get("crawl") or [{}], key=lambda x: x.get("Date") or "")
    # per-page stats are thin, so the CTR check uses ~13 weeks of buckets
    # Bing lists some pages under both the apex and www host: merge them by path
    pages = [dict(x, page=SITE + "/" + x["page"].split(DOMAIN + "/", 1)[-1]) for x in b["pages"]]
    last_seen = defaultdict(str)
    for x in pages:
        if x["date"] and x["impressions"]:
            last_seen[x["page"]] = max(last_seen[x["page"]], x["date"])
    recent = {x["page"]: x["impressions"] for x in top(pages, "page")}
    low = bing_low_ctr(top(pages, "page", (d(e) - dt.timedelta(days=BING_CTR_DAYS)).isoformat()))
    # a 13-week total can be one old burst (e.g. back-to-school): only flag pages Bing still shows
    res["low_ctr_pages"] = [dict(x, recent_impressions=recent[x["page"]], last_seen=last_seen[x["page"]])
                            for x in low if recent.get(x["page"])]
    return res


BING_CTR_DAYS = 91
# impression-weighted Bing position buckets used to find a page's peers
BING_POS_BUCKETS = [(0, 3), (3, 5), (5, 8), (8, 12), (12, 1000)]


def poisson_cdf(k, lam):
    """P(X <= k) for X ~ Poisson(lam)."""
    term = total = math.exp(-lam)
    for i in range(1, int(k) + 1):
        term *= lam / i
        total += term
    return total


def bing_low_ctr(pages):
    """Pages whose Bing clicks are well below what the site's OTHER pages at a
    similar position get (leave-one-out peer CTR), and unlikely to be chance
    (Poisson P(X <= clicks) < 0.05). A site-relative check, not a universal
    CTR threshold."""
    pages = [p for p in pages if p["position"]]
    bucket = lambda pos: next(i for i, (lo, hi) in enumerate(BING_POS_BUCKETS) if lo <= pos < hi)
    tot = defaultdict(lambda: [0, 0])
    for p in pages:
        t = tot[bucket(p["position"])]
        t[0] += p["clicks"]
        t[1] += p["impressions"]
    out = []
    for p in pages:
        c, i = tot[bucket(p["position"])]
        peer_imp = i - p["impressions"]
        if peer_imp < 500:
            continue
        peer_ctr = (c - p["clicks"]) / peer_imp
        expected = peer_ctr * p["impressions"]
        if expected < 3:
            continue
        pval = poisson_cdf(p["clicks"], expected)
        if pval < 0.05:
            out.append(dict(p, peer_ctr=peer_ctr, expected=expected, p=pval))
    return sorted(out, key=lambda x: -(x["expected"] - x["clicks"]))


EFFORT_WEIGHT = {"S": 1, "M": 2, "L": 4}


def rank_opportunities(r, cfg, running=()):
    """Top 10 by estimated upside per unit of effort. Pages inside a running
    experiment are held back: changing them again would make the experiment
    unreadable."""
    ops = []
    for p in r.get("low_ctr_pages", []):
        ops.append({"type": "Title/description test", "page": p["page"], "effort": "S",
                    "upside": p["upside"],
                    "evidence": f"{fmt_n(p['impressions'])} impressions at avg position {p['position']:.1f} "
                                f"but CTR {fmt_pct(p['ctr'], False)} (planning assumption for that "
                                f"position: {fmt_pct(expected_ctr(p['position'], cfg), False)})",
                    "action": "Rewrite title/description to match the top queries' wording and intent; "
                              "check what the SERP shows for those queries first."})
    for p in (r.get("bing") or {}).get("low_ctr_pages", []):
        ops.append({"type": "Bing: title/description test", "page": p["page"], "effort": "S",
                    "upside": (p["expected"] - p["clicks"]) * 28 / BING_CTR_DAYS,
                    "evidence": f"Bing, last ~13 weeks: {fmt_n(p['impressions'])} impressions at avg position "
                                f"{p['position']:.1f}, {fmt_n(p['clicks'])} clicks; the site's other pages at that "
                                f"position average {fmt_pct(p['peer_ctr'], False)} CTR (≈{p['expected']:.0f} clicks "
                                f"expected, p = {p['p']:.3f}). Still shown: {fmt_n(p['recent_impressions'])} "
                                f"impressions in the last 4 weeks.",
                    "action": "Check the Bing queries this page appears for and what Bing shows for them, then "
                              "rewrite the title/description to answer that query directly."})
    for p in r.get("striking_pages", []):
        qs =", ".join(f"'{q['query']}' (#{q['position']:.0f})" for q in
                       sorted(p["queries"], key=lambda q: -q["impressions"])[:3])
        ops.append({"type": "Near first page: strengthen content", "page": p["page"], "effort": "M",
                    "upside": p["upside"],
                    "evidence": f"{fmt_n(p['impressions'])} impressions on queries ranked 4-20, e.g. {qs}",
                    "action": "Answer those queries more directly on the page, add internal links from "
                              "related pages using that wording, and check the page fully matches intent."})
    for x in r.get("declining", []):
        ops.append({"type": "Investigate decline", "page": x["page"], "effort": "S",
                    "upside": max(0, x["c0"] - x["c1"]) + 0.01 * max(0, x["i0"] - x["i1"]),
                    "evidence": f"clicks {fmt_n(x['c0'])} -> {fmt_n(x['c1'])}, impressions {fmt_n(x['i0'])} -> "
                                f"{fmt_n(x['i1'])} (28d vs previous 28d)",
                    "action": "Check URL inspection, recent edits (git log), query mix and SERP changes "
                              "before changing anything."})
    for c in r.get("cannibal", []):
        ops.append({"type": "Pages competing for one query", "page": c["pages"][0]["page"], "effort": "M",
                    "upside": 0.02 * c["impressions"],
                    "evidence": f"'{c['query']}' ({fmt_n(c['impressions'])} impr) split across "
                                + ", ".join(path_of(x["page"]) for x in c["pages"]),
                    "action": "Decide which page should own the query; differentiate or link the others to it. "
                              "Consolidate only if the pages genuinely overlap."})
    for x in (r.get("ga4") or {}).get("low_engagement", []):
        ops.append({"type": "Low engagement from search", "page": x["landingPage"], "effort": "M",
                    "upside": 0.1 * x["sessions"],
                    "evidence": f"{fmt_n(x['sessions'])} organic sessions, engagement rate "
                                f"{fmt_pct(x['engagementRate'], False)} vs site organic average "
                                f"{fmt_pct(r['ga4']['landing_avg_er'], False)}",
                    "action": "Check the page delivers what the landing queries ask for above the fold, "
                              "on mobile, quickly."})
    un = r.get("unseen")
    if un and un["by_section"]:
        k, n, tot = un["by_section"][0]
        ops.append({"type": "Indexing/visibility", "page": k, "effort": "M", "upside": 0.5 * n,
                    "evidence": f"{n} of {tot} sitemap URLs in {k} had zero Search impressions in the period",
                    "action": "URL-inspect a sample; if 'Discovered/Crawled - not indexed', improve "
                              "uniqueness and internal links rather than requesting indexing in bulk."})
    # not indexed, and Google's last crawl predates our last edit: it hasn't seen the new page
    seen = set()
    for x in r.get("inspections") or []:
        if x["url"] in seen or not x.get("coverageState") or "not indexed" not in x["coverageState"]:
            continue
        seen.add(x["url"])
        f = url_to_file(x["url"])
        edited = subprocess.run(["git", "log", "-1", "--format=%ad", "--date=short", "--", f], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip() if f else ""
        crawled = (x.get("lastCrawlTime") or "")[:10]
        if edited and (not crawled or crawled < edited):
            ops.append({"type": "Request recrawl", "page": x["url"], "effort": "S", "upside": 2,
                        "evidence": f"{x['coverageState']}; last crawled {crawled or 'never'}, "
                                    f"page last changed {edited}",
                        "action": "Search Console > URL Inspection > Request indexing (manual; a few pages "
                                  "only), and link to it from a page Google crawls often."})
    for o in ops:
        o["score"] = o["upside"] / EFFORT_WEIGHT[o["effort"]]
    ops.sort(key=lambda o: -o["score"])
    out, held, per_type, seen_pages = [], [], defaultdict(int), set()
    for o in ops:
        exp = next((eid for eid, rx in running if rx.search(o["page"])), None)
        if exp and o["type"] != "Request recrawl":  # a recrawl request doesn't change the page
            if o["page"] not in seen_pages:
                held.append(dict(o, experiment=exp))
                seen_pages.add(o["page"])
            continue
        if per_type[o["type"]] >= 4 or o["page"] in seen_pages:
            continue
        per_type[o["type"]] += 1
        seen_pages.add(o["page"])
        out.append(o)
        if len(out) == 10:
            break
    for i, o in enumerate(out, 1):
        o["id"] = f"T{i}"
    return out, held[:10]


# ---------------------------------------------------------------- experiments

def gsc_page_regex(regex):
    """Experiment regexes match URL paths ("^/exam-calendar\\.html$"), but Search Console's page
    dimension is the full URL, so a path anchor must be moved past the scheme and host."""
    return "^https?://[^/]+" + regex[1:] if regex.startswith("^/") else regex


def window_daily(gsc, site, regex, start, end):
    rows = gsc.query(site, start, end, ["date"],
                     filters=[{"dimension": "page", "operator": "includingRegex", "expression": gsc_page_regex(regex)}])
    return rows


GA4_MIN_SESSIONS = 50  # per group and window before the GA4 comparison says anything


def ga4_landing_groups(ga_client, start, end, treat_regex, control_regex):
    """Organic sessions landing on the treatment pages vs the control pages.
    screenPageViews per landingPage counts every view in those sessions, so
    views/session is how far visitors go after landing."""
    ga, prop = ga_client
    rows = ga.report(prop, start, end, ["landingPage"], ["sessions", "screenPageViews", "engagedSessions"],
                     organic_only=True)
    t, c = re.compile(treat_regex), re.compile(control_regex)
    groups = {g: {"sessions": 0, "screenPageViews": 0, "engagedSessions": 0} for g in ("treatment", "control")}
    for r in rows:
        page = r["landingPage"].split("?")[0]
        g = "treatment" if t.search(page) else "control" if c.search(page) else None
        if g:
            for m in groups[g]:
                groups[g][m] += r[m]
    for g in groups.values():
        n = g["sessions"]
        g["views_per_session"] = round(g["screenPageViews"] / n, 3) if n else None
        g["engaged_rate"] = round(g["engagedSessions"] / n, 4) if n else None
    return groups


def ga4_compare(pre, post):
    """Difference-in-differences of treatment vs control, pre vs post.
    The engaged-rate change gets a two-proportion z; views/session has no
    per-session variance in aggregate GA4 data, so it is descriptive only."""
    cells = [pre["treatment"], post["treatment"], pre["control"], post["control"]]
    if min(c["sessions"] for c in cells) < GA4_MIN_SESSIONS:
        return {"note": f"fewer than {GA4_MIN_SESSIONS} organic sessions in a group/window; not compared"}
    dd_vps = ((post["treatment"]["views_per_session"] - pre["treatment"]["views_per_session"])
              - (post["control"]["views_per_session"] - pre["control"]["views_per_session"]))
    dd_er = ((post["treatment"]["engaged_rate"] - pre["treatment"]["engaged_rate"])
             - (post["control"]["engaged_rate"] - pre["control"]["engaged_rate"]))
    se = math.sqrt(sum(c["engaged_rate"] * (1 - c["engaged_rate"]) / c["sessions"] for c in cells))
    return {"dd_views_per_session": round(dd_vps, 3), "dd_engaged_rate": round(dd_er, 4),
            "z_engaged_rate": round(dd_er / se, 2) if se else 0}


def bing_compare(snap, regex, start, n):
    """Bing page stats for the experiment pages vs the rest of the site.
    Bing reports weekly buckets and it isn't clear whether a bucket's date
    starts or ends its week, so buckets dated within 7 days either side of
    the change are skipped; neither window then contains a mixed week."""
    rows = (snap.get("bing") or {}).get("pages") or []
    if not rows:
        return None
    rx = re.compile(regex)
    lo, gap = (start - dt.timedelta(days=n + 7)).isoformat(), (start - dt.timedelta(days=7)).isoformat()
    post_from = (start + dt.timedelta(days=7)).isoformat()
    cells = {w: {g: {"clicks": 0, "impressions": 0} for g in ("treatment", "control")} for w in ("pre", "post")}
    weeks = {"pre": set(), "post": set()}
    for r in rows:
        w = "pre" if lo <= r["date"] < gap else "post" if r["date"] >= post_from else None
        if not w:
            continue
        path = "/" + r["page"].split(DOMAIN + "/", 1)[-1]
        g = "treatment" if rx.search(path) else "control"
        cells[w][g]["clicks"] += r["clicks"]
        cells[w][g]["impressions"] += r["impressions"]
        weeks[w].add(r["date"])
    out = {"pre_weeks": len(weeks["pre"]), "post_weeks": len(weeks["post"]), **cells}
    if not weeks["pre"] or not weeks["post"]:
        return out
    scale = len(weeks["post"]) / len(weeks["pre"])
    for m in ("clicks", "impressions"):
        c_pre, c_post = cells["pre"]["control"][m], cells["post"]["control"][m]
        trend = (c_post / scale) / c_pre if c_pre else 1
        expected = cells["pre"]["treatment"][m] * scale * trend
        out[m] = {"expected_from_site_trend": round(expected, 1),
                  "z": round((cells["post"]["treatment"][m] - expected) / math.sqrt(expected), 2) if expected > 0 else 0}
    return out


def evaluate_experiments(experiments, snap, gsc_client, ga_client=None):
    """Compare each running experiment's pages before vs after the change,
    against the rest of the site over the same days as a control. Experiments
    with a "ga4_engagement" control_regex also get a GA4 comparison of organic
    sessions landing on their pages vs those control pages. Every experiment
    gets the same comparison on Bing page stats; "primary_source": "bing" makes
    the verdict use Bing instead of Search Console."""
    results = []
    end = d(snap["meta"]["end"])
    today = dt.date.today().isoformat()
    for ex in experiments:
        if ex.get("status") not in ("running", None):
            results.append({"id": ex["id"], "status": ex["status"], "summary": ex.get("next_action", "")})
            continue
        start = d(ex["date"])
        n = ex.get("window_days", 28)
        pre = (start - dt.timedelta(days=n), start - dt.timedelta(days=1))
        post_start = start + dt.timedelta(days=3)  # recrawl buffer
        post_end = min(post_start + dt.timedelta(days=n - 1), end)
        post_days = (post_end - post_start).days + 1
        if not gsc_client:
            results.append({"id": ex["id"], "status": "pending",
                            "summary": "Needs Search Console API data (export has no per-page daily rows)."})
            continue
        gsc, site = gsc_client
        t_pre = agg(window_daily(gsc, site, ex["pages_regex"], *pre))
        site_pre = agg(gsc.query(site, pre[0], pre[1], ["date"]))
        ex.setdefault("baseline", {"window": [pre[0].isoformat(), pre[1].isoformat()], **t_pre})
        g_pre = None
        if ga_client and ex.get("ga4_engagement"):
            ctrl = ex["ga4_engagement"]["control_regex"]
            g_pre = ga4_landing_groups(ga_client, *pre, ex["pages_regex"], ctrl)
            ex.setdefault("ga4_baseline", {"window": [pre[0].isoformat(), pre[1].isoformat()], **g_pre})
        bing = bing_compare(snap, ex["pages_regex"], start, n)
        if bing and bing["pre_weeks"]:
            ex.setdefault("bing_baseline", {"weeks": bing["pre_weeks"], **bing["pre"]})
        if post_days < 7:
            results.append({"id": ex["id"], "status": "too early",
                            "summary": f"Only {max(post_days, 0)} days of post-change data; baseline recorded "
                                       f"({fmt_n(t_pre['clicks'])} clicks, {fmt_n(t_pre['impressions'])} impressions "
                                       f"in {n} days before)."
                                       + (f" GA4 baseline: {fmt_n(g_pre['treatment']['sessions'])} organic sessions "
                                          f"landing on these pages, {fmt_n(g_pre['treatment']['views_per_session'], 2)} "
                                          f"views/session." if g_pre else "")
                                       + (f" Bing baseline: {fmt_n(bing['pre']['treatment']['clicks'])} clicks, "
                                          f"{fmt_n(bing['pre']['treatment']['impressions'])} impressions in "
                                          f"{bing['pre_weeks']} weeks." if bing and bing["pre_weeks"] else ""),
                            "bing": bing})
            continue
        t_post = agg(window_daily(gsc, site, ex["pages_regex"], post_start, post_end))
        site_post = agg(gsc.query(site, post_start, post_end, ["date"]))
        scale = post_days / n
        ev = {"run_date": today, "post_window": [post_start.isoformat(), post_end.isoformat()]}
        for m in ("clicks", "impressions"):
            c_pre = site_pre[m] - t_pre[m]
            c_post = site_post[m] - t_post[m]
            trend = (c_post / scale) / c_pre if c_pre else 1
            expected = t_pre[m] * scale * trend
            z = (t_post[m] - expected) / math.sqrt(expected) if expected > 0 else 0
            ev[m] = {"pre": t_pre[m], "post": t_post[m], "expected_from_site_trend": round(expected, 1),
                     "z": round(z, 2)}
        ev["ctr"] = {"pre": t_pre["ctr"], "post": t_post["ctr"]}
        ev["position"] = {"pre": t_pre["position"], "post": t_post["position"]}
        if g_pre:
            # no recrawl lag for on-page behaviour: start the day after deploy
            g_post = ga4_landing_groups(ga_client, start + dt.timedelta(days=1), post_end,
                                        ex["pages_regex"], ex["ga4_engagement"]["control_regex"])
            ev["ga4"] = {"pre": g_pre, "post": g_post,
                         "post_window": [(start + dt.timedelta(days=1)).isoformat(), post_end.isoformat()],
                         **ga4_compare(g_pre, g_post)}
        if bing:
            ev["bing"] = bing
        metric = ex["metric"] if ex["metric"] in ("clicks", "impressions") else "clicks"
        if ex.get("primary_source") == "bing":
            # Bing sends most of these pages' search visitors, so judge on Bing
            b_clicks = (bing["pre"]["treatment"]["clicks"] + bing["post"]["treatment"]["clicks"]) if bing else 0
            conclusive = today >= ex["evaluate_after"] and bing and metric in bing and b_clicks >= 30
            mz = bing[metric]["z"] if conclusive else 0
        else:
            conclusive = today >= ex["evaluate_after"] and t_post["clicks"] + t_pre["clicks"] >= 30
            mz = ev[metric]["z"]
        if not conclusive:
            ev["verdict"] = "interim -- not conclusive yet"
        elif mz >= 2:
            ev["verdict"] = "better than the site trend predicts (not proof of cause)"
        elif mz <= -2:
            ev["verdict"] = "worse than the site trend predicts"
        else:
            ev["verdict"] = "no clear effect beyond normal fluctuation"
        ex.setdefault("evaluations", [])
        ex["evaluations"] = [e for e in ex["evaluations"] if e["run_date"] != today] + [ev]
        results.append({"id": ex["id"], "status": ev["verdict"], "eval": ev,
                        "summary": f"{ex['metric']}: {fmt_n(ev[ex['metric']]['pre'] if ex['metric'] in ev else 0)} "
                                   f"before vs {fmt_n(ev[ex['metric']]['post'] if ex['metric'] in ev else 0)} after "
                                   f"({post_days} of {n} post days)"})
    return results


# ---------------------------------------------------------------- report

def url_to_file(page):
    p = path_of(page).lstrip("/")
    if not p or p.endswith("/"):
        p += "index.html"
    return p if os.path.exists(os.path.join(ROOT, p)) else None


def review_previous(prev_plan):
    """Did last week's tasks get done? Detected from git history, not assumed."""
    out = []
    for t in prev_plan.get("tasks", []):
        f = url_to_file(t["page"]) if t.get("page", "").startswith("http") else None
        status = "no page file to check"
        if f:
            log = subprocess.run(["git", "log", f"--since={prev_plan['run_date']}", "--format=%h %ad %s",
                                  "--date=short", "--", f], cwd=ROOT, capture_output=True, text=True).stdout.strip()
            status = f"changed: {log.splitlines()[0]}" if log else "no commit touching this page since the plan"
        out.append((t, status))
    return out


def render_report(snap, cfg, r, exp_results, prev_plan, run_date):
    L = []
    w = snap["windows"]
    src = snap["meta"]["source"]
    L.append(f"# Weekly SEO report — {DOMAIN} — {run_date}\n")
    if src == "export":
        L.append(f"> **Data source: manual Search Console export** (`{snap['meta']['export_file']}`, "
                 f"{snap['meta'].get('export_range')}, last day {snap['meta']['end']}). GA4 and AdSense are not "
                 "connected yet. Page/query/country tables cover the whole export range, so page-level "
                 "period comparisons and declining-page detection are not possible in this report.\n")
    else:
        L.append(f"> Data: Search Console `{snap['gsc']['site'] if snap.get('gsc') else 'n/a'}`, "
                 f"GA4 `{snap['ga4']['property'] if snap.get('ga4') else 'n/a'}`, "
                 f"AdSense `{snap['adsense']['account'] if snap.get('adsense') else 'n/a'}`. "
                 f"Last complete day: {snap['meta']['end']} (Search Console data lags ~{cfg['gsc_lag_days']} days).\n")
    L.append(f"Windows — last 7d: {w['cur7'][0]}..{w['cur7'][1]} · last 28d: {w['cur28'][0]}..{w['cur28'][1]} · "
             f"previous 28d: {w['prev28'][0]}..{w['prev28'][1]}\n")

    # 1 summary
    L.append("## 1. Traffic and revenue summary\n")
    p = r.get("periods")
    if p:
        c28 = p["cur28"]
        L.append(f"- **Search clicks (Search Console):** {fmt_n(c28['clicks'])} in 28 days "
                 f"(≈{c28['clicks'] / 28:.1f}/day), {fmt_n(c28['impressions'])} impressions, "
                 f"CTR {fmt_pct(c28['ctr'], False)}, avg position {fmt_n(c28['position'], 1)}")
    ga = r.get("ga4")
    if ga:
        u = ga["organic_users_per_day"]
        L.append(f"- **Organic users (GA4):** ≈{u['cur28']:.1f}/day over 28 days, ≈{u['cur7']:.1f}/day last 7 days "
                 f"— goal {ga['goal']:,}/day ({u['cur28'] / ga['goal']:.2%} of goal). "
                 f"All-channel users 28d: {fmt_n(ga['windows']['cur28']['users_all'])}.")
        src = ga.get("organic_sources") or []
        tot = sum(x["totalUsers"] for x in src)
        if tot:
            L.append("  - Organic users by search engine (28d): " + ", ".join(
                f"{x['sessionSource']} {x['totalUsers']:.0f} ({x['totalUsers'] / tot:.0%})" for x in src[:6]) +
                ". Search Console only covers Google.")
    else:
        L.append(f"- **Organic users (GA4):** not available — {snap['errors'].get('ga4', 'not fetched')}")
    bg = r.get("bing")
    if bg:
        b28, b0 = bg["windows"]["cur28"], bg["windows"]["prev28"]
        L.append(f"- **Bing clicks (Bing Webmaster Tools):** {fmt_n(b28['clicks'])} in 28 days "
                 f"(≈{b28['clicks'] / 28:.1f}/day; previous 28d {fmt_n(b0['clicks'])}, {bg['signal28']}), "
                 f"{fmt_n(b28['impressions'])} impressions. Covers Bing and Yahoo.")
    elif "bing" in snap["errors"]:
        L.append(f"- **Bing:** not available — {snap['errors']['bing']}")
    ad = r.get("adsense")
    if ad:
        a28 = ad["windows"]["cur28"]
        cur = ad["currency"]
        L.append(f"- **AdSense:** {cur} {a28['earnings']:,.2f} estimated earnings in 28 days, "
                 f"{fmt_n(a28['page_views'])} page views, page RPM {cur} {a28['rpm']:.2f}")
    else:
        L.append(f"- **AdSense:** not available — {snap['errors'].get('adsense', 'not fetched')}")
    L.append("\n*Search Console clicks ≠ GA4 users/sessions: clicks count search-result clicks (incl. users "
             "who block analytics or leave before the tag fires); GA4 counts tagged visits and de-duplicates "
             "users. Expect them to differ.*\n")

    # 2 changes
    L.append("## 2. Changes versus previous periods\n")
    if p:
        L.append("| Comparison | Clicks | Impressions | CTR | Avg position |")
        L.append("|---|---|---|---|---|")
        for c in r["comparisons"]:
            if "unavailable" in c:
                L.append(f"| {c['label']} | {c['unavailable']} | | | |")
                continue
            cl, im = c["clicks"], c["impressions"]
            L.append(f"| {c['label']} | {fmt_n(cl[1])} → {fmt_n(cl[0])} ({fmt_pct(cl[2])}; {cl[3]}) | "
                     f"{fmt_n(im[1])} → {fmt_n(im[0])} ({fmt_pct(im[2])}; {im[3]}) | "
                     f"{fmt_pct(c['ctr'][1], False)} → {fmt_pct(c['ctr'][0], False)} | "
                     f"{fmt_n(c['position'][1], 1)} → {fmt_n(c['position'][0], 1)} |")
        L.append("\n*Signal label = Welch t-test on daily values; a rough guide to whether a change is "
                 "bigger than normal day-to-day noise, not proof of a trend or its cause.*\n")
    if ga:
        u = ga["organic_users_per_day"]
        L.append(f"- GA4 organic users/day: previous 28d {u['prev28']:.1f} → last 28d {u['cur28']:.1f} "
                 f"({fmt_pct(pct(u['cur28'], u['prev28']))}; {ga['organic_trend_signal']}); "
                 f"previous 7d {u['prev7']:.1f} → last 7d {u['cur7']:.1f}")
    if ad:
        a, b = ad["windows"]["cur28"], ad["windows"]["prev28"]
        cur = ad["currency"]
        L.append(f"- AdSense earnings ({cur}): {b['earnings']:,.2f} → {a['earnings']:,.2f} "
                 f"({fmt_pct(pct(a['earnings'], b['earnings']))}; {ad['signal28']}); "
                 f"RPM {b['rpm']:.2f} → {a['rpm']:.2f}")
    L.append("")

    # 3 winners
    L.append("## 3. Top 10 pages (by Search clicks) and why they may be succeeding\n")
    if r.get("top_pages"):
        L.append("| Page | Clicks | Impr. | CTR | Pos. | Change vs prev 28d |")
        L.append("|---|---|---|---|---|---|")
        for x in r["top_pages"]:
            ch = ""
            if r.get("page_cmp") and x["page"] in r["page_cmp"]:
                pc = r["page_cmp"][x["page"]]
                ch = f"clicks {fmt_n(pc['c0'])}→{fmt_n(pc['c1'])}, impr {fmt_n(pc['i0'])}→{fmt_n(pc['i1'])}"
            L.append(f"| `{path_of(x['page'])}` | {fmt_n(x['clicks'])} | {fmt_n(x['impressions'])} | "
                     f"{fmt_pct(x['ctr'], False)} | {x['position']:.1f} | {ch} |")
        L.append("\n*Why: see the queries driving each page in section 5; the analyst notes give a "
                 "hypothesis, not a proven cause.*\n")

    # 4 opportunities and decliners
    L.append("## 4. Top 10 opportunities and declining pages\n")
    ops = r.get("opportunities", [])
    if ops:
        L.append("| # | Type | Page | Evidence | Effort | Est. extra clicks/28d* |")
        L.append("|---|---|---|---|---|---|")
        for o in ops:
            L.append(f"| {o['id']} | {o['type']} | `{path_of(o['page']) if o['page'].startswith('http') else o['page']}` | "
                     f"{o['evidence']} | {o['effort']} | {o['upside']:.0f} |")
        L.append("\n*\\*Scenario estimate from the CTR planning assumptions in `seo/config.json` (Bing rows: the "
                 "gap to the site's own Bing CTR at that position), not a forecast. "
                 "Use it to rank work, not to predict traffic.*\n")
    if r.get("held_back"):
        L.append("**Held back — page is inside a running experiment (revisit after it is evaluated):**\n")
        for o in r["held_back"]:
            L.append(f"- `{path_of(o['page'])}` ({o['experiment']}): {o['type']} — {o['evidence']}")
        L.append("")
    if r.get("declining") is not None:
        if r["declining"]:
            L.append("**Declining pages (beyond normal fluctuation):**\n")
            for x in r["declining"]:
                L.append(f"- `{path_of(x['page'])}` clicks {fmt_n(x['c0'])}→{fmt_n(x['c1'])}, "
                         f"impressions {fmt_n(x['i0'])}→{fmt_n(x['i1'])}, position "
                         f"{fmt_n(x['pos0'], 1)}→{fmt_n(x['pos1'], 1)}")
        else:
            L.append("No page declined by more than normal fluctuation.")
    else:
        L.append("_Declining-page detection needs the API (two comparable periods per page)._")
    L.append("")

    # 5 queries
    L.append("## 5. Search queries worth targeting\n")
    sq = r.get("striking_queries", [])
    if sq:
        L.append("**Near the first page (avg position 4–20):**\n")
        L.append("| Query | Page | Impr. | Clicks | Pos. |")
        L.append("|---|---|---|---|---|")
        for x in sq[:15]:
            L.append(f"| {x['query']} | {('`' + path_of(x['page']) + '`') if x.get('page') else '—'} | "
                     f"{fmt_n(x['impressions'])} | {fmt_n(x['clicks'])} | {x['position']:.1f} |")
        L.append("")
    if r.get("content_gaps"):
        L.append("**Demand with no page ranking in the top 20** (evidence for improving or adding content):\n")
        for x in r["content_gaps"][:10]:
            L.append(f"- {x['query']} — {fmt_n(x['impressions'])} impressions, best position {x['position']:.0f}")
        L.append("")
    if r.get("rising_queries"):
        L.append("**Rising queries (impressions up beyond noise):** " +
                 ", ".join(f"{x['query']} ({fmt_n(x['i0'])}→{fmt_n(x['i1'])})" for x in r["rising_queries"][:10]) + "\n")
    if r.get("cannibal"):
        L.append("**Queries split across several pages:**\n")
        for c in r["cannibal"][:5]:
            L.append(f"- {c['query']} ({fmt_n(c['impressions'])} impr): " +
                     ", ".join(f"`{path_of(x['page'])}` #{x['position']:.0f}" for x in c["pages"]))
        L.append("")

    # 6 changes completed
    L.append("## 6. Content and technical changes completed\n")
    since = (prev_plan or {}).get("run_date") or (d(run_date) - dt.timedelta(days=7)).isoformat()
    log = subprocess.run(["git", "log", f"--since={since}", "--date=short", "--format=- %h %ad %s"],
                         cwd=ROOT, capture_output=True, text=True).stdout.strip()
    L.append(f"Commits since {since}:\n\n{log or '_none_'}\n")

    # 7 experiments
    L.append("## 7. Results of previous experiments\n")
    if exp_results:
        L.append("| Experiment | Status | Detail |")
        L.append("|---|---|---|")
        for e in exp_results:
            L.append(f"| {e['id']} | {e['status']} | {e['summary']} |")
        L.append("\n*Each experiment is compared with the rest of the site over the same days (a control for "
                 "site-wide and seasonal swings). Changes shipped together on the same days cannot be "
                 "separated from each other.*\n")
        bing_rows = [(e["id"], e.get("eval", {}).get("bing") or e.get("bing")) for e in exp_results]
        bing_rows = [(i, b) for i, b in bing_rows if b and b["pre_weeks"] and b["post_weeks"]]
        if bing_rows:
            L.append("**Bing page stats (weekly buckets; the weeks next to the change are skipped)**\n")
            L.append("| Experiment | Weeks before / after | Clicks before → after | Expected from site trend | z | "
                     "Impressions before → after | Expected | z |")
            L.append("|---|---|---|---|---|---|---|---|")
            for i, b in bing_rows:
                t0, t1 = b["pre"]["treatment"], b["post"]["treatment"]
                L.append(f"| {i} | {b['pre_weeks']} / {b['post_weeks']} | {fmt_n(t0['clicks'])} → {fmt_n(t1['clicks'])} | "
                         f"{fmt_n(b['clicks']['expected_from_site_trend'], 1)} | {b['clicks']['z']} | "
                         f"{fmt_n(t0['impressions'])} → {fmt_n(t1['impressions'])} | "
                         f"{fmt_n(b['impressions']['expected_from_site_trend'], 1)} | {b['impressions']['z']} |")
            L.append("\n*Bing covers Bing and Yahoo, about 60% of this site's organic visitors. Compared with the rest "
                     "of the site's Bing page stats over the same weeks; |z| < 2 is within normal fluctuation. "
                     "Impression z-scores overstate certainty (impressions are not independent events), so "
                     "verdicts use clicks.*\n")
        ga4_rows = [e for e in exp_results if e.get("eval", {}).get("ga4")]
        for e in ga4_rows:
            g = e["eval"]["ga4"]
            L.append(f"**{e['id']} — GA4, organic sessions by landing page** "
                     f"(after: {g['post_window'][0]}..{g['post_window'][1]})\n")
            L.append("| Group | Window | Sessions | Views/session | Engaged rate |")
            L.append("|---|---|---|---|---|")
            for grp in ("treatment", "control"):
                for win in ("pre", "post"):
                    c = g[win][grp]
                    L.append(f"| {grp} | {'before' if win == 'pre' else 'after'} | {fmt_n(c['sessions'])} | "
                             f"{fmt_n(c['views_per_session'], 2)} | {fmt_pct(c['engaged_rate'], False)} |")
            if "note" in g:
                L.append(f"\n{g['note']}.\n")
            else:
                L.append(f"\nChange beyond the control: views/session {g['dd_views_per_session']:+.2f} "
                         f"(descriptive), engaged rate {g['dd_engaged_rate'] * 100:+.1f} points (z = {g['z_engaged_rate']}). "
                         "|z| < 2 is within normal fluctuation.\n")
    if prev_plan:
        L.append(f"**Last plan ({prev_plan['run_date']}) — implementation check from git:**\n")
        for t, status in review_previous(prev_plan):
            L.append(f"- {t['id']} {t['type']} `{path_of(t['page']) if t['page'].startswith('http') else t['page']}` — {status}")
        L.append("")

    # 8 tasks
    L.append("## 8. Prioritized tasks for the coming week\n")
    for o in ops[:5]:
        page = path_of(o["page"]) if o["page"].startswith("http") else o["page"]
        L.append(f"{o['id']}. **{o['type']} — `{page}`** ({o['effort']}): {o['action']}")
    L.append("\nEach change ships as its own small commit and gets an entry in `seo/experiments.json` "
             "(hypothesis, metric, date) before it is deployed.\n")

    # 9 risks
    L.append("## 9. Risks, uncertainties and missing data\n")
    for name, err in snap["errors"].items():
        L.append(f"- **{name}:** {err}")
    if ga and ga.get("ad_pages_note"):
        L.append(f"- {ga['ad_pages_note']}")
    if ga and ga.get("likely_bots"):
        b = ga["likely_bots"]
        L.append(f"- **Likely automated traffic:** {sum(x['sessions'] for x in b):,.0f} sessions (28d) from cities with "
                 "~0% engagement — " + ", ".join(f"{x['city']} / {x['sessionDefaultChannelGroup']} {x['sessions']:.0f}"
                                                  for x in b[:5]) +
                 ". It inflates all-channel users; the goal metric (organic users) is barely affected.")
    if ad and ad["other_domains"]:
        L.append("- The AdSense account also served ads on (56 days, excluded above): " +
                 "; ".join(f"{k} — {v[1]:,.0f} page views, {ad['currency']} {v[0]:.2f}"
                           for k, v in ad["other_domains"]))
    if p and p["cur28"]["clicks"] < 300:
        L.append(f"- Small numbers: {fmt_n(p['cur28']['clicks'])} clicks in 28 days means most page-level "
                 "changes cannot be distinguished from noise yet; expect to judge experiments on impressions "
                 "and position first.")
    L.append("- The last ~2 days of Search Console data are excluded because they are incomplete.")
    un = r.get("unseen")
    if un:
        L.append(f"- {un['count']} of {un['total']} sitemap URLs had no Search impressions in the period "
                 f"(not necessarily unindexed — some may be indexed but never shown).")
    insp = r.get("inspections")
    if insp:
        states = defaultdict(int)
        for x in insp:
            states[x.get("coverageState") or x.get("error", "?")] += 1
        L.append("- URL inspection sample: " + ", ".join(f"{k}: {v}" for k, v in sorted(states.items(), key=lambda kv: -kv[1])))
    L.append("")

    # 10 next best actions
    L.append("## 10. Next best actions toward 3,000 organic users/day\n")
    if ga:
        L.append(f"Current organic users ≈{ga['organic_users_per_day']['cur28']:.1f}/day.")
    elif p:
        L.append(f"Current Search clicks ≈{p['cur28']['clicks'] / 28:.1f}/day (GA4 not yet connected).")
    L.append("See analyst notes (if present) and tasks above. The automated list ranks by evidence in the "
             "data; it cannot judge content quality or SERP features — review each before acting.\n")

    # appendix
    if r.get("countries"):
        L.append("## Appendix — countries and devices (Search Console)\n")
        L.append("| Country | Clicks | Impr. | Pos. |")
        L.append("|---|---|---|---|")
        for c in r["countries"]:
            L.append(f"| {c['country']} | {fmt_n(c['clicks'])} | {fmt_n(c['impressions'])} | {c['position']:.1f} |")
        L.append("")
        L.append(" · ".join(f"{x['device']}: {fmt_n(x['clicks'])} clicks / {fmt_n(x['impressions'])} impr"
                            for x in r["devices"]) + "\n")
    if bg:
        L.append(f"## Appendix — Bing (`{bg['site']}`, ≈ last 4 weekly buckets)\n")
        L.append("*Bing reports query/page stats in weekly buckets; positions are Bing's average impression "
                 "position as reported.*\n")
        for title, rows, key in (("Top queries", bg["queries"], "query"), ("Top pages", bg["pages"], "page")):
            if not rows:
                L.append(f"{title}: no data.\n")
                continue
            L.append(f"**{title}:**\n")
            L.append(f"| {key.title()} | Clicks | Impr. | Pos. |")
            L.append("|---|---|---|---|")
            for x in rows[:15]:
                label = f"`{path_of(x[key])}`" if key == "page" else x[key]
                L.append(f"| {label} | {fmt_n(x['clicks'])} | {fmt_n(x['impressions'])} | {fmt_n(x['position'], 1)} |")
            L.append("")
        cl = {k: v for k, v in bg["crawl_latest"].items() if isinstance(v, (int, float)) or k == "Date"}
        if cl:
            L.append("**Latest Bing crawl stats:** " + ", ".join(f"{k} {v}" for k, v in cl.items()) + "\n")
    if ga and ga.get("ad_pages"):
        cur = (ad or {}).get("currency", "")
        L.append(f"## Appendix — ad revenue by page (GA4, AdSense-linked; site RPM {cur} {ga['site_rpm_ga4']:.2f})\n")
        L.append("| Page | Views | Ad impressions | Revenue | RPM |")
        L.append("|---|---|---|---|---|")
        for x in ga["ad_pages"]:
            L.append(f"| `{x['pagePath']}` | {fmt_n(x['screenPageViews'])} | {fmt_n(x['publisherAdImpressions'])} | "
                     f"{x['totalAdRevenue']:.2f} | {x['rpm']:.2f} |")
        L.append("")
    if insp:
        bad, seen = [], set()
        for x in insp:
            if x["url"] not in seen and x.get("coverageState") != "Submitted and indexed":
                seen.add(x["url"])
                bad.append(x)
        if bad:
            L.append("## Appendix — inspected URLs that are not indexed\n")
            L.append("| URL | Coverage | Last crawled | Google canonical |")
            L.append("|---|---|---|---|")
            for x in bad:
                gc = x.get("googleCanonical") or ""
                L.append(f"| `{path_of(x['url'])}` | {x.get('coverageState') or x.get('error')} | "
                         f"{(x.get('lastCrawlTime') or 'never')[:10]} | {'' if gc in ('', x['url']) else gc} |")
            L.append("")
    if un and un["by_section"]:
        L.append("**Sitemap URLs with zero impressions, by section:** " +
                 ", ".join(f"{k} {n}/{t}" for k, n, t in un["by_section"][:12]) + "\n")

    plan = {"run_date": run_date, "source": src,
            "tasks": [{k: o[k] for k in ("id", "type", "page", "action", "evidence", "effort", "upside")} for o in ops]}
    return "\n".join(L) + "\n", plan
