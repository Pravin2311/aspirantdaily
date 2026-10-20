"""Write content_inventory.json: one record per HTML page on the site.

Everything here is derived from the files in the repository, git history and,
when present, the Search Console Page-indexing exports in "search console/".
Nothing is estimated: there is no traffic, ranking or keyword-volume data, so
those fields are absent rather than guessed.

Usage:
  python scripts/build_inventory.py              # writes content_inventory.json
  python scripts/build_inventory.py --stdout     # print instead
"""
import argparse
import csv
import glob
import json
import os
import re
from collections import Counter
from datetime import date
from urllib.parse import urlparse

from seo_lib import HOST, ROOT, canonical_of, git_dates, html_pages, is_indexable, robots_of, soup_for, url_for

OFFICIAL = re.compile(
    r"(\.gov\.in|\.nic\.in|rbi\.org\.in|upsc\.gov\.in|ssc\.gov\.in|ibps\.in|sbi\.co\.in|sbi\.bank\.in|"
    r"indiacode\.nic\.in|legislative\.gov\.in|sci\.gov\.in|pib\.gov\.in|isro\.gov\.in|un\.org|unfccc\.int|"
    r"who\.int|wipo\.int|imf\.org|worldbank\.org|ramsar\.org|unesco\.org|ncert\.nic\.in)$")
EXAMS = {
    "UPSC": r"\bUPSC\b|Civil Services|\bIAS\b|Prelims",
    "SSC": r"\bSSC\b|\bCGL\b|\bCHSL\b|\bMTS\b",
    "Banking": r"\bIBPS\b|\bSBI\b|RBI Grade B|bank exams?|Banking Awareness",
    "Railway": r"\bRRB\b|\bNTPC\b|Group D|Railway",
    "State PSC": r"State PSC|\bUPPSC\b|\bMPPSC\b|\bTNPSC\b|\bBPSC\b|\bRPSC\b",
}
SUBJECTS = ["polity", "history", "geography", "environment", "economy", "science-tech", "ir", "schemes",
            "current-affairs", "quant", "reasoning", "english", "computer", "static-gk", "banking"]


def page_type(rel):
    name = os.path.basename(rel)
    if rel == "index.html":
        return "homepage"
    if rel in ("quiz.html", "quiz-selector.html", "result.html"):
        return "quiz-app"
    if rel in ("admin.html",):
        return "admin"
    if rel in ("contact.html", "privacy-policy.html", "terms.html"):
        return "legal-utility"
    if rel == "exam-calendar.html":
        return "exam-directory"
    if name == "index.html":
        return "hub"
    if rel.startswith("study/current-affairs/"):
        return "current-affairs-explainer"
    if rel.startswith("study/"):
        return "study-note"
    if rel.startswith("repeated-questions/"):
        return "revision-cheat-code"
    if "syllabus" in name:
        return "exam-syllabus-guide"
    if re.search(r"vs-|strategy|how-to|score|attempt|which", name):
        return "exam-strategy-guide"
    if re.search(r"mcq|current-affairs", name):
        return "current-affairs-archive"
    return "blog-topic-guide"


INTENT = {
    "homepage": "navigational", "hub": "navigational (subject index)", "quiz-app": "practice tool",
    "admin": "none", "legal-utility": "navigational", "exam-directory": "exam information (official links)",
    "study-note": "informational: learn a topic", "current-affairs-explainer": "informational: understand an event or policy",
    "revision-cheat-code": "revision: quick facts", "exam-syllabus-guide": "exam information: syllabus and pattern",
    "exam-strategy-guide": "exam information: strategy", "current-affairs-archive": "revision: monthly current affairs",
    "blog-topic-guide": "informational: topic list or explainer",
}


def subject_of(rel):
    parts = rel.split("/")
    if parts[0] == "study" and len(parts) > 2:
        return parts[1]
    name = os.path.basename(rel).replace(".html", "")
    for s in SUBJECTS:
        if s in name:
            return s
    for key, s in (("polity", "polity"), ("geography", "geography"), ("bank", "banking"), ("puzzle", "reasoning"),
                   ("current-affairs", "current-affairs"), ("important-days", "static-gk"), ("rrb-group-d-science", "science-tech")):
        if key in name:
            return s
    return "general"


def main_text(soup):
    body = soup.body
    if body is None:
        return ""
    for tag in body.find_all(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    return re.sub(r"\s+", " ", body.get_text(" ")).strip()


def shingles(text, n=5):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def gsc_issues():
    """URL -> list of 'issue (export date)' from Page-indexing drilldown exports."""
    out = {}
    folder = os.path.join(ROOT, "search console")
    for sub in sorted(glob.glob(os.path.join(folder, "*", ""))):
        meta_p, table_p = os.path.join(sub, "Metadata.csv"), os.path.join(sub, "Table.csv")
        if not (os.path.exists(meta_p) and os.path.exists(table_p)):
            continue
        with open(meta_p, encoding="utf-8-sig") as fh:
            meta = {r[0]: r[1] for r in csv.reader(fh) if len(r) >= 2}
        issue = meta.get("Issue") or meta.get("issue") or "unknown issue"
        stamp = re.search(r"\d{4}-\d{2}-\d{2}", os.path.basename(os.path.dirname(sub)) or sub)
        with open(table_p, encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                url = row.get("URL") or next(iter(row.values()))
                out.setdefault(url, []).append(f"{issue} (export {stamp.group(0) if stamp else '?'})")
    return out


def build():
    gsc = gsc_issues()
    records, texts = [], {}
    inlinks = Counter()
    for rel in html_pages():
        soup = soup_for(rel)
        for a in soup.find_all("a", href=True):
            href = a["href"].split("#")[0].split("?")[0]
            if not href or href.startswith(("http", "mailto:", "javascript:")):
                if href.startswith(HOST):
                    href = urlparse(href).path
                else:
                    continue
            target = os.path.normpath(os.path.join(os.path.dirname(rel), href)) if not href.startswith("/") else href.lstrip("/")
            target = target.replace(os.sep, "/")
            if target in ("", "."):
                target = "index.html"
            if target.endswith("/"):
                target += "index.html"
            if target != rel:
                inlinks[target] += 1
    for rel in html_pages():
        soup = soup_for(rel)
        title = soup.title.get_text(strip=True) if soup.title else ""
        desc_tag = soup.find("meta", attrs={"name": "description"})
        h1 = soup.find("h1")
        ext = [a["href"] for a in soup.find_all("a", href=True) if a["href"].startswith("http") and not a["href"].startswith(HOST)]
        domains = sorted({urlparse(u).netloc.lower().removeprefix("www.") for u in ext})
        official = sorted(d for d in domains if OFFICIAL.search(d))
        h2s = [h.get_text(" ", strip=True) for h in soup.find_all("h2")]
        mcqs = len(soup.select(".mcq-item")) or len(re.findall(r"<p class=\"mcq-question\"|class=\"q-card\"", str(soup)))
        tables = len(soup.find_all("table"))
        ld_types = []
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(s.string or "")
                for item in data if isinstance(data, list) else [data]:
                    ld_types.append(item.get("@type"))
            except (ValueError, AttributeError):
                ld_types.append("INVALID")
        text = main_text(soup)
        texts[rel] = shingles(text)
        exams = [e for e, pat in EXAMS.items() if len(re.findall(pat, text)) >= 2]
        ptype = page_type(rel)
        first, last = git_dates(rel)
        url = url_for(rel)
        apex = url.replace("https://www.", "https://")
        if official:
            quality = "cites official/primary sources"
        elif domains:
            quality = "cites secondary sources only"
        else:
            quality = "no external citations"
        records.append({
            "url": url, "path": rel, "page_type": ptype, "subject": subject_of(rel),
            "title": title, "h1": h1.get_text(" ", strip=True) if h1 else "",
            "meta_description": desc_tag.get("content", "") if desc_tag else "",
            "canonical": (canonical_of(soup) or [None])[0], "robots": robots_of(soup) or "(default index,follow)",
            "indexable": is_indexable(rel, soup), "exam_audience": exams or ["general"],
            "likely_search_intent": INTENT[ptype],
            "available_content": {"words": len(text.split()), "h2_sections": h2s[:20], "mcqs": mcqs,
                                  "tables": tables, "structured_data": ld_types},
            "source_quality": quality, "official_domains_cited": official, "external_domains_cited": domains,
            "internal_inlinks": inlinks.get(rel, 0),
            "first_published": first, "last_substantive_change": last,
            "gsc_issues_reported": gsc.get(url, []) + [f"apex URL: {i}" for i in gsc.get(apex, [])],
            "overlaps_with": [],
        })
    # Overlap: share of the smaller page's 5-word shingles found in the other page.
    rels = [r["path"] for r in records]
    by_rel = {r["path"]: r for r in records}
    for i, a in enumerate(rels):
        for b in rels[i + 1:]:
            sa, sb = texts[a], texts[b]
            if len(sa) < 50 or len(sb) < 50:
                continue
            share = len(sa & sb) / min(len(sa), len(sb))
            if share >= 0.12:
                by_rel[a]["overlaps_with"].append({"path": b, "shared_5gram_share": round(share, 2)})
                by_rel[b]["overlaps_with"].append({"path": a, "shared_5gram_share": round(share, 2)})
    return {
        "generated": date.today().isoformat(),
        "host": HOST,
        "notes": [
            "Derived from repository files and git history only. No traffic, ranking or keyword-volume data exists in the repo, so none is recorded.",
            "gsc_issues_reported comes from Page-indexing drilldown samples exported 2026-10-18, before the canonical fix was deployed; they are samples, not totals.",
            "overlaps_with lists pages sharing at least 12% of the smaller page's 5-word sequences (template text such as footers is excluded).",
            "source_quality only says which domains a page links to; it is not a fact-check.",
        ],
        "summary": {
            "pages": len(records),
            "indexable": sum(r["indexable"] for r in records),
            "by_page_type": dict(Counter(r["page_type"] for r in records).most_common()),
            "by_subject": dict(Counter(r["subject"] for r in records if r["indexable"]).most_common()),
            "by_source_quality": dict(Counter(r["source_quality"] for r in records if r["indexable"]).most_common()),
            "quiz_bank_questions": quiz_bank(),
        },
        "pages": records,
    }


def quiz_bank():
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "*.json"))):
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        qs = data if isinstance(data, list) else data.get("questions", [])
        out[os.path.basename(f)] = len(qs)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()
    inv = build()
    text = json.dumps(inv, indent=2, ensure_ascii=False) + "\n"
    if args.stdout:
        print(text)
    else:
        with open(os.path.join(ROOT, "content_inventory.json"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print(f"content_inventory.json: {inv['summary']['pages']} pages, {inv['summary']['indexable']} indexable")
