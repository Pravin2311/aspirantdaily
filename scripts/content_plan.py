"""Build CONTENT_MASTER_PLAN.csv from the topic lists, the inventory and pipeline state.

Checks run every time (the build fails on errors):
  * every planned slug and URL is unique and does not collide with an existing page;
  * no two planned pages target the same search intent (query/title token overlap);
  * planned pages that overlap an existing page that is not their declared parent are flagged.

Usage:
  python scripts/content_plan.py            # write CONTENT_MASTER_PLAN.csv and print totals
  python scripts/content_plan.py --check    # validate only
"""
import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict

from content_lib import (CATEGORIES, INVENTORY, PAGE_TYPES, PLAN_CSV, SOURCES, hub_for, load_state, parents_for,
                         read_topics, url_of)

STOP = set("""a an the of and or in on to for with by from vs v is are what how why when which its their
explained explanation meaning key list notes guide basics types""".split())
COLUMNS = ["id", "status", "action", "category", "subtopic", "page_type", "url", "proposed_title",
           "primary_search_intent", "intended_exams", "audience", "learning_outcome", "primary_source_requirements",
           "related_existing_pages", "internal_links_to_add", "priority", "batch", "quality_bar", "notes"]

VERIFIED_EXISTING = {
    "blog/upsc-prelims-syllabus-2025.html": "Verified 2026-10-20 against UPSC Notice 05/2026-CSE",
    "blog/ssc-cgl-syllabus-2025.html": "Verified 2026-10-20 against the SSC CGL 2026 notice",
    "blog/how-to-score-180-ssc-cgl-tier1.html": "Pattern facts verified 2026-10-20 against the SSC CGL 2026 notice",
    "exam-calendar.html": "Official-source directory; no unverified dates",
}


def tokens(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and w}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def existing_category(rec):
    p, s = rec["path"], rec["subject"]
    if rec["page_type"] in ("homepage", "hub", "quiz-app", "admin", "legal-utility"):
        return None
    if p == "study/science-tech/computer-and-it-fundamentals.html" or "computer" in p or "puzzles" in p:
        return "Reasoning and Computer Awareness"
    if s == "polity":
        return "Indian Polity and Constitution"
    if s == "history":
        return "History and Culture"
    if s in ("geography", "environment"):
        return "Geography and Environment"
    if s == "quant":
        return "Quantitative Aptitude"
    if s == "english":
        return "English Language"
    if s in ("economy", "science-tech", "banking"):
        return "Economy and General Science"
    if s in ("current-affairs", "ir", "schemes", "static-gk"):
        return "Current Affairs and Static GK"
    if rec["page_type"] in ("exam-syllabus-guide", "exam-strategy-guide", "exam-directory"):
        return "Exam-Specific Guides"
    if "important-days" in p:
        return "Current Affairs and Static GK"
    return "Exam-Specific Guides"


def existing_action(rec):
    p, t = rec["path"], rec["page_type"]
    if p == "blog/current-affairs-dec-2025-summary.html":
        return "merge", "Merge into blog/top-25-current-affairs-mcqs-december-2025.html (28% shared text, same month) with a 308 redirect"
    if p == "blog/top-25-current-affairs-mcqs-december-2025.html":
        return "keep", "Merge target for the December 2025 summary"
    if p in VERIFIED_EXISTING:
        return "keep", "Re-verify when the next official notice is published"
    if p in ("blog/bank-exam-syllabus-2025.html", "blog/rrb-syllabus-2025.html", "blog/psc-syllabus-2025.html"):
        return "improve", "Verify against the current official notices before retitling (sources listed in SEO_AUDIT.md)"
    if p == "study/current-affairs/digital-personal-data-protection-act.html":
        return "improve", "Add the DPDP Rules 2025 (Gazette notification) here instead of creating a separate URL"
    if t == "current-affairs-explainer":
        return "improve", "Add primary-source citations and a dated 'as of' line; check for template boilerplate"
    if t == "study-note":
        return "improve", "Add source citations; link to the deep-dive pages planned for this subtopic"
    if t == "revision-cheat-code":
        return "improve", "Add sources; make every fact dated where it can change"
    return "improve", "Add sources; differentiate from overlapping pages"


def build(check_only=False):
    if not os.path.exists(INVENTORY):
        sys.exit("content_inventory.json is missing; run: python -X utf8 scripts/build_inventory.py")
    with open(INVENTORY, encoding="utf-8") as fh:
        inv = json.load(fh)
    existing = {r["path"]: r for r in inv["pages"]}
    state = load_state()
    errors, warnings = [], []

    topics = list(read_topics())
    seen_ids, seen_paths = {}, {}
    for t in topics:
        if t["id"] in seen_ids:
            errors.append(f"duplicate slug {t['id']}: {seen_ids[t['id']]} and {t['topic_file']}")
        seen_ids[t["id"]] = t["topic_file"]
        if t["path"] in existing:
            errors.append(f"{t['topic_file']}: {t['path']} already exists — improve that page instead")
        if t["path"] in seen_paths:
            errors.append(f"duplicate URL {t['path']}")
        seen_paths[t["path"]] = t["id"]

    # Duplicate-intent check between planned pages.
    tok = {t["id"]: (tokens(t["primary_query"]), tokens(t["title"]), t["page_type"]) for t in topics}
    ids = [t["id"] for t in topics]
    for i, a in enumerate(ids):
        qa, ta, pa = tok[a]
        for b in ids[i + 1:]:
            qb, tb, pb = tok[b]
            if (pa == "mcq") != (pb == "mcq"):
                continue  # practice sets and explainers serve different intents
            if jaccard(qa, qb) >= 0.75 or (jaccard(ta, tb) >= 0.75 and jaccard(qa, qb) >= 0.5):
                errors.append(f"duplicate intent: {a} vs {b}")
    # Overlap with existing pages.
    overlaps = defaultdict(list)
    ex_tok = {p: tokens(r["title"] + " " + r["h1"]) for p, r in existing.items() if r["indexable"]}
    for t in topics:
        qa = tokens(t["primary_query"]) | tokens(t["title"])
        for p, et in ex_tok.items():
            score = jaccard(qa, et)
            if score >= 0.35:
                overlaps[t["id"]].append((p, round(score, 2)))
                if p not in parents_for(t):
                    warnings.append(f"{t['id']} overlaps existing {p} ({score:.2f}) which is not its parent")

    batch_of = {}
    for name, b in state.get("batches", {}).items():
        for pid in b["ids"]:
            batch_of[pid] = name

    rows = []
    by_sub = defaultdict(list)
    for t in topics:
        by_sub[(t["category"], t["subtopic"])].append(t)
    for t in topics:
        ps = state["pages"].get(t["id"], {})
        status = ps.get("status", "planned")
        parents = [p for p in parents_for(t) if p in existing]
        siblings = [s["path"] for s in by_sub[(t["category"], t["subtopic"])] if s["id"] != t["id"]]
        mcq = [s["path"] for s in by_sub[(t["category"], t["subtopic"])] if s["page_type"] == "mcq" and s["id"] != t["id"]]
        links_out = [hub_for(t["folder"])] + parents + mcq[:1] + [s for s in siblings if s not in mcq][:3]
        notes = []
        if overlaps.get(t["id"]):
            notes.append("overlaps existing: " + "; ".join(f"{p} ({s})" for p, s in overlaps[t["id"]]))
        rows.append({
            "id": t["id"], "status": status, "action": "new", "category": t["category"], "subtopic": t["subtopic"],
            "page_type": PAGE_TYPES[t["page_type"]], "url": url_of(t["path"]), "proposed_title": t["title"],
            "primary_search_intent": t["primary_query"], "intended_exams": ", ".join(t["exams"]),
            "audience": ", ".join(t["exams"]) + " aspirants", "learning_outcome": t["learning_outcome"],
            "primary_source_requirements": " ; ".join(SOURCES[k] for k in t["source_keys"]),
            "related_existing_pages": " ; ".join(parents),
            "internal_links_to_add": "out: " + " ; ".join(links_out) + (" | in: from " + " ; ".join(parents) if parents else ""),
            "priority": t["priority"], "batch": batch_of.get(t["id"], ""),
            "quality_bar": "not yet drafted" if status == "planned" else ps.get("quality_bar", status),
            "notes": " ; ".join(notes),
        })
    for p, r in sorted(existing.items()):
        cat = existing_category(r)
        if cat is None or not r["indexable"]:
            continue
        action, note = existing_action(r)
        rows.append({
            "id": "existing:" + p, "status": "published", "action": action, "category": cat, "subtopic": r["subject"],
            "page_type": r["page_type"], "url": r["url"], "proposed_title": r["title"],
            "primary_search_intent": r["likely_search_intent"], "intended_exams": ", ".join(r["exam_audience"]),
            "audience": ", ".join(r["exam_audience"]) + " aspirants", "learning_outcome": "",
            "primary_source_requirements": "; ".join(r["official_domains_cited"]) or "none cited yet",
            "related_existing_pages": "; ".join(o["path"] for o in r["overlaps_with"]),
            "internal_links_to_add": "", "priority": "", "batch": "",
            "quality_bar": VERIFIED_EXISTING.get(p, "Not yet: " + r["source_quality"] + "; not editorially fact-checked"),
            "notes": note,
        })

    totals = {}
    for cat, (_f, target) in CATEGORIES.items():
        new = sum(1 for r in rows if r["category"] == cat and r["action"] == "new")
        ex = sum(1 for r in rows if r["category"] == cat and r["action"] in ("keep", "improve"))
        merged = sum(1 for r in rows if r["category"] == cat and r["action"] == "merge")
        totals[cat] = {"target": target, "existing_kept": ex, "existing_merging": merged, "new_planned": new,
                       "planned_total": ex + new}
    status_counts = Counter(r["status"] for r in rows if r["action"] == "new")

    if not check_only and not errors:
        with open(PLAN_CSV, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    return rows, totals, status_counts, errors, warnings


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    rows, totals, status_counts, errors, warnings = build(args.check)
    for e in errors:
        print("ERROR", e)
    if args.verbose:
        for w in warnings:
            print("WARN ", w)
    print(f"{'category':38} target existing new  total")
    for cat, t in totals.items():
        print(f"{cat:38} {t['target']:6} {t['existing_kept']:8} {t['new_planned']:4} {t['planned_total']:6}")
    print(f"{'TOTAL':38} {sum(t['target'] for t in totals.values()):6} "
          f"{sum(t['existing_kept'] for t in totals.values()):8} {sum(t['new_planned'] for t in totals.values()):4} "
          f"{sum(t['planned_total'] for t in totals.values()):6}")
    print("new-page status:", dict(status_counts), f"| {len(warnings)} overlap warnings")
    sys.exit(1 if errors else 0)
