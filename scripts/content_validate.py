"""Quality gates for content drafts.

A draft is content/drafts/<id>.html: a JSON metadata block followed by
<section data-heading="..."> blocks of HTML. See CONTENT_MASTER_PLAN.md for the
format. validate_draft() returns (errors, warnings, review_items, scorecard).

Automated validation only proves structural and arithmetic facts: the right
fields exist, numbers in worked examples and answer keys recompute, text is not
duplicated, links resolve. It never proves a factual claim; every claim is
listed as a review item for a human editor.
"""
import ast
import json
import math
import operator
import os
import re
from datetime import date
from fractions import Fraction
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from content_lib import PRIMARY_DOMAINS, ROOT
from seo_lib import html_pages, soup_for

META_RE = re.compile(r'<script type="application/json" id="draft-meta">(.*?)</script>', re.S)
SECTION_RE = re.compile(r'<section data-heading="([^"]+)">(.*?)</section>', re.S)
MIN_WORDS = {"guide": 900, "method": 800, "revision": 450, "mcq": 250, "exam": 600, "ca": 600}
MIN_MCQS = {"mcq": 15}
REQUIRED = ["id", "title", "h1", "description", "subtitle", "page_type", "exams", "primary_query",
            "learning_outcome", "sources", "claims", "drafted_by"]
BANNED = [
    (r"\bwe guarantee\b|\bguarantee[sd]?\s+(you\s+)?(a\s+|your\s+)?(selection|success|marks|score|results?|rank|qualif\w*)\b"
     r"|\bguaranteed\s+(selection|success|marks|score|results?|rank)\b", "promises results ('guarantee')"),
    (r"\b100\s*%\s*(selection|success|score|marks|result)", "promises results ('100%')"),
    (r"\bsure[- ]shot\b", "promises results ('sure-shot')"),
    (r"\btoppers?\b", "unsupported 'toppers' claim"),
    (r"\bfree marks\b", "promises results ('free marks')"),
    (r"\brepeats? (every|each) year\b|\bevery year without fail\b", "unsupported repetition claim"),
    (r"\bfact[- ]checked\b|\bexpert[- ]reviewed\b|\bverified by (our )?(experts?|team)\b", "page must not declare its own review status"),
    (r"\b(our|a team of) (experts|IAS officers|toppers|faculty)\b", "unsupported authority claim"),
    (r"\bwritten by (an? )?(IAS|IPS|IRS) officer\b", "fake credential"),
    (r"\b(asked|appeared|came) in (UPSC|SSC|IBPS|SBI|RRB|CGL|CHSL|prelims)\b[^.<]{0,40}\b(19|20)\d\d\b", "previous-year attribution needs an official PYQ source"),
    (r"\bPYQ\b", "previous-year attribution needs an official PYQ source"),
]
WARN_PHRASES = [(r"\bclick here\b", "vague link text"), (r"\bmost (important|repeated)\b", "superlative without evidence")]


# ---------- safe arithmetic for checks ----------

def _letter_pos(ch):
    return ord(ch.upper()) - 64


def _letter(n):
    return chr((int(n) - 1) % 26 + 65)


def _shift(word, k):
    return "".join(_letter(_letter_pos(c) + k) if c.isalpha() else c for c in word)


def _reverse_letter(ch):
    return _letter(27 - _letter_pos(ch))


def _weekday(y, m, d):
    return date(int(y), int(m), int(d)).strftime("%A")


def _ratio(a, b):
    """Simplest form of a : b as text, e.g. ratio(14, 6) -> '7 : 3'."""
    fa, fb = Fraction(a), Fraction(b)
    scale = math.lcm(fa.denominator, fb.denominator)
    ia, ib = int(fa * scale), int(fb * scale)
    g = math.gcd(ia, ib)
    return f"{ia // g} : {ib // g}"


def _compass(x, y):
    """Eight-point direction of the displacement (x east, y north), e.g. compass(3, 3) -> 'North-East'."""
    names = ["East", "North-East", "North", "North-West", "West", "South-West", "South", "South-East"]
    return names[round(math.degrees(math.atan2(y, x)) / 45) % 8]


def _sind(x):
    return math.sin(math.radians(x))


def _cosd(x):
    return math.cos(math.radians(x))


def _tand(x):
    return math.tan(math.radians(x))


FUNCS = {
    "sqrt": math.sqrt, "isqrt": math.isqrt, "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
    "comb": math.comb, "perm": math.perm, "factorial": math.factorial, "gcd": math.gcd, "lcm": math.lcm,
    "log": math.log, "log10": math.log10, "exp": math.exp, "floor": math.floor, "ceil": math.ceil,
    "sind": _sind, "cosd": _cosd, "tand": _tand, "degrees": math.degrees, "atand": lambda x: math.degrees(math.atan(x)),
    "abs": abs, "round": round, "min": min, "max": max, "pow": pow, "Fraction": Fraction, "int": int, "float": float,
    "pos": _letter_pos, "letter": _letter, "shift": _shift, "rev": _reverse_letter,
    "revword": lambda w: "".join(_reverse_letter(c) if c.isalpha() else c for c in w), "weekday": _weekday,
    "hypot": math.hypot, "ratio": _ratio, "compass": _compass,
}
CONSTS = {"pi": math.pi, "e": math.e}
BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
          ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
UNOPS = {ast.USub: operator.neg, ast.UAdd: operator.pos}
CMPOPS = {ast.Eq: operator.eq, ast.Lt: operator.lt, ast.Gt: operator.gt, ast.LtE: operator.le, ast.GtE: operator.ge,
          ast.NotEq: operator.ne}


def safe_eval(expr):
    """Evaluate arithmetic with a whitelist of functions. No names, attributes or calls outside FUNCS."""
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in BINOPS:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and isinstance(right, (int, float)) and abs(right) > 1000:
                raise ValueError("exponent too large")
            return BINOPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in UNOPS:
            return UNOPS[type(node.op)](ev(node.operand))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in CMPOPS:
            return CMPOPS[type(node.ops[0])](ev(node.left), ev(node.comparators[0]))
        if isinstance(node, ast.Name) and node.id in CONSTS:
            return CONSTS[node.id]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCS and not node.keywords:
            return FUNCS[node.func.id](*[ev(a) for a in node.args])
        if isinstance(node, (ast.Tuple, ast.List)):
            return [ev(e) for e in node.elts]
        raise ValueError(f"disallowed expression element: {type(node).__name__}")
    return ev(ast.parse(expr, mode="eval"))


def values_match(got, expect):
    if isinstance(expect, list) and len(expect) == 2 and all(isinstance(x, (int, float)) for x in expect):
        return isinstance(got, (int, float, Fraction)) and abs(float(got) - expect[0]) <= expect[1]
    if isinstance(expect, str):
        return str(got) == expect
    if isinstance(got, (int, float, Fraction)) and isinstance(expect, (int, float)):
        return math.isclose(float(got), float(expect), rel_tol=1e-9, abs_tol=1e-9)
    return got == expect


NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def first_number(text):
    m = NUM_RE.search(text.replace("−", "-"))
    return float(m.group(0).replace(",", "")) if m else None


# ---------- parsing ----------

def parse_draft(text):
    m = META_RE.search(text)
    if not m:
        raise ValueError("no <script type=\"application/json\" id=\"draft-meta\"> block")
    meta = json.loads(m.group(1))
    body = text[m.end():]
    sections = [(h, html.strip()) for h, html in SECTION_RE.findall(body)]
    leftover = SECTION_RE.sub("", body).strip()
    return meta, sections, leftover


def visible_text(html):
    soup = BeautifulSoup(html, "lxml")
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def paragraphs(html):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for tag in soup.find_all(["p", "li", "td"]):
        t = re.sub(r"\s+", " ", tag.get_text(" ")).strip().lower()
        if len(t.split()) >= 12:
            out.append(t)
    return out


def shingles(text, n=5):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


_SITE_CACHE = {}


def site_corpus():
    """Paragraphs, shingles, titles and h1s of every page currently on the site."""
    if "c" in _SITE_CACHE:
        return _SITE_CACHE["c"]
    paras, shing, titles, h1s = {}, {}, {}, {}
    for rel in html_pages():
        soup = soup_for(rel)
        titles[rel] = soup.title.get_text(strip=True) if soup.title else ""
        h = soup.find("h1")
        h1s[rel] = h.get_text(" ", strip=True) if h else ""
        body = soup.body
        if body is None:
            continue
        for t in body.find_all(["script", "style", "nav", "header", "footer", "noscript"]):
            t.decompose()
        html = str(body)
        for p in paragraphs(html):
            paras.setdefault(p, rel)
        shing[rel] = shingles(body.get_text(" "))
    _SITE_CACHE["c"] = (paras, shing, titles, h1s)
    return _SITE_CACHE["c"]


def resolve_link(href, page_path):
    """Site-relative target path for an internal href, or None for external links."""
    href = href.split("#")[0].split("?")[0]
    if not href or href.startswith(("mailto:", "tel:", "javascript:")):
        return None
    if href.startswith("http"):
        u = urlparse(href)
        if u.netloc not in ("www.aspirantdaily.com", "aspirantdaily.com"):
            return None
        href = u.path
    if href.startswith("/"):
        target = href.lstrip("/")
    else:
        target = os.path.normpath(os.path.join(os.path.dirname(page_path), href)).replace(os.sep, "/")
    if target in ("", "."):
        target = "index.html"
    if target.endswith("/"):
        target += "index.html"
    return target


# ---------- validation ----------

def validate_draft(text, plan_row, other_drafts=None, root=ROOT, today=None):
    """Return (errors, warnings, review_items, scorecard)."""
    today = today or date.today().isoformat()
    errors, warnings, review = [], [], []
    try:
        meta, sections, leftover = parse_draft(text)
    except (ValueError, json.JSONDecodeError) as exc:
        return [f"cannot parse draft: {exc}"], [], [], {"automated": "fail"}

    for key in REQUIRED:
        if not meta.get(key) and meta.get(key) != []:
            errors.append(f"missing metadata field '{key}'")
    if leftover:
        errors.append("content outside <section data-heading> blocks")
    if meta.get("id") != plan_row["id"]:
        errors.append(f"draft id {meta.get('id')!r} does not match plan id {plan_row['id']!r}")
    ptype = meta.get("page_type", "")
    if ptype not in MIN_WORDS:
        errors.append(f"unknown page_type {ptype!r}")
    page_path = plan_row["path"]

    title = meta.get("title", "")
    full_title = f"{title} | AspirantDaily"
    if len(full_title) > 75:
        errors.append(f"title too long ({len(full_title)} chars with suffix; max 75)")
    if len(title) < 20:
        errors.append("title too short")
    desc = meta.get("description", "")
    if not 70 <= len(desc) <= 165:
        errors.append(f"meta description is {len(desc)} chars (70-165)")
    if len(sections) < 3:
        errors.append(f"only {len(sections)} sections (min 3)")

    body_html = "\n".join(h for _, h in sections)
    soup = BeautifulSoup(body_html, "lxml")
    if soup.find("h1"):
        errors.append("body must not contain <h1> (the renderer adds it)")
    if soup.find("script") or soup.find("iframe"):
        errors.append("body must not contain scripts or iframes")
    if soup.find(attrs={"onclick": True}) or re.search(r"\son\w+=", body_html):
        errors.append("inline event handlers are not allowed")
    if soup.find(attrs={"style": True}):
        warnings.append("inline style attributes; prefer existing classes")

    mcqs = meta.get("mcqs", [])
    faq = meta.get("faq", [])
    prose = visible_text(body_html)
    mcq_text = " ".join(q.get("q", "") + " " + q.get("explanation", "") for q in mcqs)
    faq_text = " ".join(f.get("q", "") + " " + f.get("a", "") for f in faq)
    all_text = " ".join([prose, mcq_text, faq_text, title, meta.get("h1", ""), desc, meta.get("subtitle", "")])
    words = len(prose.split()) + len(faq_text.split())
    if ptype in MIN_WORDS and words < MIN_WORDS[ptype]:
        errors.append(f"thin content: {words} words of prose (min {MIN_WORDS[ptype]} for {ptype})")
    if ptype in MIN_MCQS and len(mcqs) < MIN_MCQS[ptype]:
        errors.append(f"MCQ set has {len(mcqs)} questions (min {MIN_MCQS[ptype]})")
    if ptype == "revision" and not soup.find("table"):
        errors.append("revision pages need at least one table")

    for pat, why in BANNED:
        m = re.search(pat, all_text, re.I)
        if m and not (why.startswith("previous-year") and any(s.get("type") == "PYQ" for s in meta.get("sources", []))):
            errors.append(f"banned claim: {why}: '{m.group(0)}'")
    for pat, why in WARN_PHRASES:
        m = re.search(pat, all_text, re.I)
        if m:
            warnings.append(f"{why}: '{m.group(0)}'")

    # Keyword stuffing.
    query = meta.get("primary_query", "").lower().strip()
    if query:
        n = len(re.findall(re.escape(query), all_text.lower()))
        if n > 3:
            errors.append(f"keyword stuffing: exact query '{query}' appears {n} times (max 3)")
        qtok = {w for w in re.findall(r"[a-z]+", query) if len(w) > 3} - {"with", "from", "what", "when", "which"}
        wl = re.findall(r"[a-z0-9]+", all_text.lower())
        if wl:
            dens = sum(1 for w in wl if w in qtok) / len(wl)
            if dens > 0.06:
                warnings.append(f"query terms are {dens:.0%} of all words")

    # Repetition within the page and boilerplate copied from the site.
    paras = paragraphs(body_html)
    dup = {p for p in paras if paras.count(p) > 1}
    for p in dup:
        errors.append(f"repeated paragraph: '{p[:70]}...'")
    site_paras, site_shing, site_titles, site_h1s = site_corpus()
    for p in set(paras):
        if len(p.split()) >= 20 and p in site_paras and site_paras[p] != page_path:
            errors.append(f"paragraph copied from {site_paras[p]}: '{p[:60]}...'")
    mine = shingles(all_text)
    max_sim, max_with = 0.0, ""
    if len(mine) > 50:
        others = dict(site_shing)
        for oid, otext in (other_drafts or {}).items():
            if oid != meta.get("id") and isinstance(otext, str):
                others["draft:" + oid] = shingles(otext)
        for rel, sh in others.items():
            if rel == page_path or len(sh) < 50:
                continue
            share = len(mine & sh) / len(mine)
            if share > max_sim:
                max_sim, max_with = share, rel
    if max_sim >= 0.30:
        errors.append(f"near-duplicate: {max_sim:.0%} of 5-word sequences also in {max_with}")
    elif max_sim >= 0.15:
        warnings.append(f"overlap: {max_sim:.0%} of 5-word sequences also in {max_with}")
    for rel, t in site_titles.items():
        if rel != page_path and t.strip().lower() == full_title.lower():
            errors.append(f"duplicate title with {rel}")
    for rel, h in site_h1s.items():
        if rel != page_path and h.strip().lower() == meta.get("h1", "").strip().lower():
            errors.append(f"duplicate H1 with {rel}")

    # Sources and claims.
    sources = meta.get("sources", [])
    src_ids = [s.get("id") for s in sources]
    if len(src_ids) != len(set(src_ids)):
        errors.append("duplicate source ids")
    primary = 0
    for s in sources:
        for k in ("id", "title", "publisher", "url", "accessed", "supports"):
            if not s.get(k):
                errors.append(f"source {s.get('id', '?')} missing '{k}'")
        u = urlparse(s.get("url", ""))
        if u.scheme not in ("http", "https") or not u.netloc:
            errors.append(f"source {s.get('id')} has an invalid URL")
            continue
        host = u.netloc.lower().removeprefix("www.")
        if PRIMARY_DOMAINS.search(host):
            primary += 1
        else:
            warnings.append(f"source {s.get('id')} ({host}) is not on the primary-source list")
        if s.get("accessed", "") > today:
            errors.append(f"source {s.get('id')} accessed date is in the future")
    claims = meta.get("claims", [])
    factual = ptype in ("guide", "revision", "exam", "ca")
    if factual and not sources:
        errors.append("factual page with no sources")
    if factual and len(claims) < 3:
        errors.append(f"factual page lists {len(claims)} claims (min 3); list the checkable facts the page relies on")
    agent_matched = 0
    for c in claims:
        if c.get("source") not in src_ids:
            errors.append(f"claim cites unknown source {c.get('source')!r}: '{c.get('text', '')[:50]}'")
        if c.get("agent_check") == "matched":
            agent_matched += 1
            if not c.get("passage"):
                warnings.append(f"claim has no supporting passage for the reviewer: '{c.get('text', '')[:50]}'")
        elif c.get("agent_check") == "not-checked":
            if not c.get("unresolved"):
                warnings.append(f"unchecked claim does not say why it is unresolved: '{c.get('text', '')[:50]}'")
        else:
            errors.append(f"claim agent_check must be 'matched' or 'not-checked': '{c.get('text', '')[:50]}'")
        review.append(("claim", c.get("text", ""), c.get("source"), c.get("locator", ""), c.get("agent_check")))
    if ptype == "ca" and not meta.get("as_of"):
        errors.append("current-affairs pages need an 'as_of' date")

    # Computation checks.
    checks = {c["id"]: c for c in meta.get("checks", [])}
    passed = 0
    for cid, c in checks.items():
        try:
            got = safe_eval(c["expr"])
        except Exception as exc:  # noqa: BLE001 - report any evaluation failure
            errors.append(f"check {cid}: cannot evaluate {c['expr']!r}: {exc}")
            continue
        if values_match(got, c["expect"]):
            passed += 1
        else:
            errors.append(f"check {cid}: {c['expr']} = {got!r}, page says {c['expect']!r}")
    referenced = set(re.findall(r'data-check="([^"]+)"', body_html))
    for cid in referenced:
        if cid not in checks:
            errors.append(f"worked example refers to undefined check '{cid}'")
    quantish = plan_row.get("category") in ("Quantitative Aptitude", "Reasoning and Computer Awareness") and ptype in ("method", "mcq")
    if quantish and len(checks) < 5:
        errors.append(f"{len(checks)} computation checks (min 5 for quant/reasoning method and MCQ pages)")

    # MCQs.
    seen_q = set()
    letters = []
    for i, q in enumerate(mcqs, 1):
        opts = q.get("options", [])
        if len(opts) != 4 or len({o.strip().lower() for o in opts}) != 4:
            errors.append(f"MCQ {i}: needs 4 distinct options")
        ans = q.get("answer")
        if not isinstance(ans, int) or not 0 <= ans < len(opts):
            errors.append(f"MCQ {i}: answer index invalid")
            continue
        letters.append(ans)
        if len(q.get("explanation", "").split()) < 10:
            errors.append(f"MCQ {i}: explanation under 10 words")
        if q.get("difficulty") not in ("easy", "medium", "hard"):
            errors.append(f"MCQ {i}: difficulty must be easy, medium or hard")
        if not q.get("topic"):
            errors.append(f"MCQ {i}: missing topic label")
        key = re.sub(r"\W+", " ", q.get("q", "").lower()).strip()
        if key in seen_q:
            errors.append(f"MCQ {i}: duplicate question")
        seen_q.add(key)
        if quantish:
            cid = q.get("check")
            if cid:
                if cid not in checks:
                    errors.append(f"MCQ {i}: check '{cid}' not defined")
                else:
                    exp = checks[cid]["expect"]
                    exp_v = exp[0] if isinstance(exp, list) else exp
                    if isinstance(exp_v, (int, float)):
                        num = first_number(opts[ans])
                        if num is None or not math.isclose(num, float(exp_v), rel_tol=1e-6, abs_tol=0.011):
                            errors.append(f"MCQ {i}: correct option '{opts[ans]}' does not match check {cid} = {exp_v}")
                    elif isinstance(exp_v, str) and exp_v.lower() not in opts[ans].lower():
                        errors.append(f"MCQ {i}: correct option '{opts[ans]}' does not contain check {cid} = {exp_v}")
            elif not q.get("check_exempt"):
                errors.append(f"MCQ {i}: needs a 'check' id or a 'check_exempt' reason")
    if len(letters) >= 8:
        top = max(letters.count(k) for k in range(4))
        if top / len(letters) > 0.4:
            warnings.append(f"answer positions unbalanced ({top} of {len(letters)} share one letter)")
    for f in faq:
        if len(f.get("a", "").split()) < 15:
            errors.append(f"FAQ answer under 15 words: '{f.get('q', '')[:50]}'")

    # Links.
    for a in soup.find_all("a", href=True):
        target = resolve_link(a["href"], page_path)
        if target is None:
            if a["href"].startswith("http") and a["href"] not in {s.get("url") for s in sources}:
                warnings.append(f"external link not listed in sources: {a['href']}")
            continue
        if os.path.exists(os.path.join(root, target)) or target in (other_drafts or {}).get("__paths__", set()):
            continue
        if target in (other_drafts or {}).get("__planned__", set()):
            warnings.append(f"links to planned page {target}; publishing waits until it is published too")
        else:
            errors.append(f"broken internal link: {a['href']} -> {target}")

    # Future years in prose (not always wrong, e.g. 2070 targets).
    this_year = int(today[:4])
    for y in sorted({int(y) for y in re.findall(r"\b(20[2-9]\d)\b", prose)}):
        if y > this_year:
            warnings.append(f"mentions future year {y}; confirm it is a target or schedule, not an event")

    scorecard = {
        "automated": "pass" if not errors else "fail",
        "words": words, "sections": len(sections), "mcqs": len(mcqs), "faq": len(faq),
        "checks_passed": f"{passed}/{len(checks)}", "sources": f"{primary} primary / {len(sources)} total",
        "claims": len(claims), "claims_agent_matched": agent_matched,
        "claims_not_checked": len(claims) - agent_matched,
        "max_overlap": f"{max_sim:.0%} ({max_with})" if max_with else "0%",
        "errors": len(errors), "warnings": len(warnings),
    }
    return errors, warnings, review, scorecard
