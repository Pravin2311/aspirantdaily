"""Batch workflow for the content library.

    python scripts/content_pipeline.py plan                       # rebuild CONTENT_MASTER_PLAN.csv
    python scripts/content_pipeline.py select [--batch-size 20] [--ids a,b,...] [--category C] [--priority P1]
    python scripts/content_pipeline.py scaffold  --batch batch-001  # empty draft files; never overwrites
    python scripts/content_pipeline.py validate  --batch batch-001
    python scripts/content_pipeline.py render    --batch batch-001  # noindex previews in content/preview/
    python scripts/content_pipeline.py report    --batch batch-001  # content/batches/batch-001-report.md (+ claims sheet)
    python scripts/content_pipeline.py claims    --batch batch-001  # refresh content/batches/batch-001-claims.csv only
    python scripts/content_pipeline.py review    --id ID --status approved --reviewer "Name" [--scope "..."] [--note "..."]
    python scripts/content_pipeline.py publish   --batch batch-001 [--dry-run]
    python scripts/content_pipeline.py status

Statuses: planned -> drafted (draft passes automated validation) -> fact-checked
(a named person confirmed every claim in the claims sheet) -> approved (a named person approved it for
publishing) -> published. Editing a draft after review resets it to drafted.

Every step is idempotent and resumable: state lives in content/state.json.
Drafts are written by people or by an optional local generator command set in
CONTENT_GENERATOR (it receives the plan row as JSON on stdin and must print a
draft). No paid API is called by this script.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import date

import content_lib
from content_lib import (BATCHES_DIR, CATEGORIES, NEW_HUBS, PREVIEW_DIR, ROOT, draft_path, file_hash,
                         hub_for, load_state, page_state, parents_for, read_topics, save_state, set_status, sha)
from content_render import HUB_NAMES, esc, hub_page, rel, render
from content_validate import parse_draft, resolve_link, validate_draft

PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2}
BLOCK_START, BLOCK_END = "<!-- content-pipeline:start -->", "<!-- content-pipeline:end -->"
NAV_RE = re.compile(r'<div class="page-navigation">.*?</div>', re.S)
SKELETON = """<script type="application/json" id="draft-meta">
{meta}
</script>

<section data-heading="Overview">
<p>TODO</p>
</section>
"""


def topics_by_id():
    return {t["id"]: t for t in read_topics()}


def batch_ids(state, name):
    if name not in state["batches"]:
        sys.exit(f"unknown batch {name}; run 'select' first")
    return state["batches"][name]["ids"]


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def batch_drafts(ids, topics):
    """Draft texts in this batch, for cross-draft duplicate checks."""
    out = {"__paths__": {topics[i]["path"] for i in ids}, "__planned__": {t["path"] for t in topics.values()}}
    for pid in ids:
        if os.path.exists(draft_path(pid)):
            try:
                meta, sections, _ = parse_draft(read(draft_path(pid)))
                out[pid] = " ".join(h for _, h in sections)
            except ValueError:
                pass
    return out


# ---------- commands ----------

def cmd_plan(_args):
    import content_plan
    rows, totals, counts, errors, _w = content_plan.build()
    for e in errors:
        print("ERROR", e)
    print(f"{len(rows)} plan rows; new-page status {dict(counts)}")
    return 1 if errors else 0


def cmd_select(args):
    state = load_state()
    topics = topics_by_id()
    in_batch = {pid for b in state["batches"].values() for pid in b["ids"]}
    if args.ids:
        ids = [i.strip() for i in args.ids.split(",") if i.strip()]
        unknown = [i for i in ids if i not in topics]
        if unknown:
            sys.exit(f"not in the plan: {unknown}")
        for name, b in state["batches"].items():
            if sorted(b["ids"]) == sorted(ids):
                print(f"{name} already holds these ids")
                return 0
        clash = [i for i in ids if i in in_batch]
        if clash:
            sys.exit(f"already in another batch: {clash}")
    else:
        pool = [t for t in topics.values() if t["id"] not in in_batch
                and page_state(state, t["id"])["status"] == "planned"
                and (not args.category or t["category"] == args.category)
                and (not args.priority or t["priority"] == args.priority)]
        order = list(topics)
        pool.sort(key=lambda t: (PRIORITY_ORDER.get(t["priority"], 9), order.index(t["id"])))
        ids = [t["id"] for t in pool[:args.batch_size]]
        if not ids:
            print("nothing left to select")
            return 0
    name = f"batch-{len(state['batches']) + 1:03d}"
    state["batches"][name] = {"ids": ids, "created": date.today().isoformat()}
    save_state(state)
    print(f"{name}: {len(ids)} pages")
    for i in ids:
        print("  ", i, topics[i]["path"])
    return 0


def cmd_scaffold(args):
    state = load_state()
    topics = topics_by_id()
    gen = os.environ.get("CONTENT_GENERATOR")
    for pid in batch_ids(state, args.batch):
        path = draft_path(pid)
        if os.path.exists(path):
            print(f"keep     {pid} (draft exists; never overwritten)")
            continue
        t = topics[pid]
        if gen:
            res = subprocess.run(gen, shell=True, input=json.dumps(t), capture_output=True, text=True,
                                 encoding="utf-8", timeout=600)
            if res.returncode != 0:
                print(f"FAILED   {pid}: generator exited {res.returncode}: {res.stderr[:200]}")
                continue
            text = res.stdout
        else:
            meta = {"id": pid, "title": t["title"], "h1": t["title"], "description": "", "subtitle": "",
                    "page_type": t["page_type"], "exams": t["exams"], "primary_query": t["primary_query"],
                    "learning_outcome": t["learning_outcome"], "sources": [], "claims": [], "checks": [],
                    "mcqs": [], "faq": [], "drafted_by": "", "notes_for_reviewer": ""}
            text = SKELETON.format(meta=json.dumps(meta, indent=2, ensure_ascii=False))
        write(path, text)
        print(f"created  {pid}")
    return 0


def run_validation(state, ids, topics):
    others = batch_drafts(ids, topics)
    results = {}
    for pid in ids:
        path = draft_path(pid)
        ps = page_state(state, pid)
        if not os.path.exists(path):
            results[pid] = (["no draft file"], [], [], {"automated": "missing"})
            continue
        text = read(path)
        res = validate_draft(text, topics[pid], other_drafts=others)
        results[pid] = res
        h = sha(text)
        errors, warnings, _review, card = res
        ps["draft_hash"] = h
        ps["scorecard"] = card
        ps["errors"] = errors
        ps["warnings"] = warnings
        reviewed = ps.get("reviewed_hash")
        if ps["status"] in ("fact-checked", "approved") and reviewed != h:
            set_status(state, pid, "drafted", "draft changed after review; review again")
            ps.pop("reviewed_hash", None)
            ps.pop("review", None)
        elif ps["status"] in ("planned", "drafted", "rejected") and not errors:
            if ps["status"] != "drafted":
                set_status(state, pid, "drafted", "passed automated validation")
        elif ps["status"] == "drafted" and errors:
            set_status(state, pid, "planned", "automated validation failing")
    return results


def cmd_validate(args):
    state = load_state()
    topics = topics_by_id()
    ids = batch_ids(state, args.batch)
    results = run_validation(state, ids, topics)
    save_state(state)
    bad = 0
    for pid, (errors, warnings, _r, card) in results.items():
        mark = "PASS" if not errors else "FAIL"
        bad += bool(errors)
        print(f"{mark} {pid}: {card.get('words', 0)} words, checks {card.get('checks_passed', '-')}, "
              f"{len(errors)} errors, {len(warnings)} warnings")
        for e in errors:
            print("     ERROR", e)
        if args.verbose:
            for w in warnings:
                print("     WARN ", w)
    print(f"{len(ids) - bad}/{len(ids)} pass automated validation")
    return 1 if bad else 0


def related_for(pid, topics, state):
    t = topics[pid]
    out = [(p, title_of(p)) for p in parents_for(t) if os.path.exists(os.path.join(ROOT, p))]
    for other in topics.values():
        if other["id"] != pid and other["subtopic"] == t["subtopic"] and other["category"] == t["category"]:
            st = page_state(state, other["id"])["status"]
            if st == "published" or os.path.exists(os.path.join(ROOT, other["path"])):
                out.append((other["path"], other["title"]))
    return out[:8]


def title_of(path):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", read(os.path.join(ROOT, path)), re.S)
    return re.sub(r"<[^>]+>|\s+", " ", m.group(1)).strip() if m else path


def cmd_render(args):
    state = load_state()
    topics = topics_by_id()
    for pid in batch_ids(state, args.batch):
        path = draft_path(pid)
        ps = page_state(state, pid)
        if not os.path.exists(path) or ps.get("errors"):
            print(f"skip     {pid} (missing or failing validation)")
            continue
        out = os.path.join(PREVIEW_DIR, topics[pid]["path"])
        html = render(read(path), topics[pid], review=ps.get("review"), preview=True,
                      related_links=related_for(pid, topics, state))
        write(out, html)
        print(f"preview  {os.path.relpath(out, ROOT)}")
    # Hubs that do not exist yet get a noindex preview, so preview links to them resolve.
    by_folder = {}
    for pid in batch_ids(state, args.batch):
        t = topics[pid]
        if t["folder"] in NEW_HUBS and not os.path.exists(os.path.join(ROOT, hub_for(t["folder"]))):
            by_folder.setdefault(t["folder"], []).append((t["path"], t["title"], t["learning_outcome"]))
    for folder, items in sorted(by_folder.items()):
        out = os.path.join(PREVIEW_DIR, hub_for(folder))
        write(out, hub_page(folder, *NEW_HUBS[folder], items, preview=True))
        print(f"preview  {os.path.relpath(out, ROOT)} (hub)")
    return 0


def cmd_report(args):
    state = load_state()
    topics = topics_by_id()
    ids = batch_ids(state, args.batch)
    results = run_validation(state, ids, topics)
    save_state(state)
    lines = [f"# {args.batch} report", "", f"Generated {date.today().isoformat()} by `scripts/content_pipeline.py report`.",
             "", "Automated validation proves structure, arithmetic, links and originality only. A page is "
             "**fact-checked** or **approved** only when a named person has recorded a review with the `review` command.",
             "", "## Scorecard", "",
             "| Page | Type | Status | Automated | Words | MCQs | Checks | Sources | Claims (agent-matched / not checked) | Editorial review | Max overlap |",
             "|---|---|---|---|---:|---:|---|---|---|---|---|"]
    for pid in ids:
        ps = page_state(state, pid)
        errors, warnings, _rv, card = results[pid]
        rev = ps.get("review")
        rev_txt = f"{rev['status']} by {rev['reviewer']} {rev['date']}" if rev else "not reviewed"
        lines.append(f"| `{topics[pid]['path']}` | {topics[pid]['page_type']} | {ps['status']} | {card.get('automated')} "
                     f"| {card.get('words', '')} | {card.get('mcqs', '')} | {card.get('checks_passed', '')} | "
                     f"{card.get('sources', '')} | {card.get('claims_agent_matched', 0)} / {card.get('claims_not_checked', 0)} "
                     f"| {rev_txt} | {card.get('max_overlap', '')} |")
    lines += ["", "## Errors and warnings", ""]
    for pid in ids:
        errors, warnings, _rv, _c = results[pid]
        if errors or warnings:
            lines.append(f"### {pid}")
            lines += [f"- ERROR {e}" for e in errors] + [f"- WARN {w}" for w in warnings] + [""]
    rows, _kept, _cleared = write_claims(args.batch, ids)
    sheet = os.path.relpath(claims_csv(args.batch), ROOT).replace(os.sep, "/")
    lines += ["## Claims for the editor to verify", "",
              f"Every claim is a row in [`{sheet}`]({os.path.basename(sheet)}) (opens in Excel or Google Sheets). "
              "For each row the editor reads `supporting_passage` at `source_url` / `locator`, then fills "
              "`reviewer_decision` (`confirmed` or `rejected`), `reviewer_name` and, if useful, `reviewer_note`.",
              "",
              "- `text-matched` means only that the drafting agent found the passage; it is **not** a fact-check.",
              "- `UNRESOLVED` means no authoritative text was opened for the claim. Confirm it from the named source, "
              "or reject it and remove the sentence from the draft.",
              "- `review --status fact-checked` is refused until every claim on the page is `confirmed` by a named person. "
              "Changing a claim in the draft clears its decision the next time the sheet is rebuilt.", "",
              "| Page | Claims | Text-matched | Unresolved | Confirmed | Rejected | Undecided |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for pid in ids:
        mine = [r for r in rows if r["page"] == pid]
        if not mine:
            continue
        dec = [r["reviewer_decision"].strip().lower() for r in mine]
        unres = sum(r["agent_status"].startswith("UNRESOLVED") for r in mine)
        lines.append(f"| {pid} | {len(mine)} | {len(mine) - unres} | {unres} | {dec.count('confirmed')} | "
                     f"{dec.count('rejected')} | {len(mine) - dec.count('confirmed') - dec.count('rejected')} |")
    lines += ["", "### Unresolved claims", ""]
    for r in rows:
        if r["agent_status"].startswith("UNRESOLVED"):
            lines.append(f"- `{r['claim_id']}` {r['claim']} — {r['agent_status'][len('UNRESOLVED: '):]}")
    for pid in ids:
        if os.path.exists(draft_path(pid)):
            note = parse_draft(read(draft_path(pid)))[0].get("notes_for_reviewer")
            if note and any(r["page"] == pid for r in rows):
                lines += ["", f"Reviewer note, {pid}: {note}"]
    lines.append("")
    res = subprocess.run([sys.executable, "-X", "utf8", os.path.join(ROOT, "scripts", "seo_check.py")],
                         capture_output=True, text=True, encoding="utf-8")
    summary = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else res.stderr[-300:]
    lines += ["## Site checks on the live pages", "",
              f"- `seo_check.py`: exit {res.returncode}; {summary}",
              "- Drafts and previews live under `content/`, which `seo_check.py` and the sitemap skip and "
              "`.vercelignore` keeps out of deployments.",
              "- Run `python -X utf8 -m unittest discover -s tests` for the route, SEO and pipeline tests.", "",
              "## To publish", "",
              "1. An editor marks every row of the claims sheet, reads the page in `content/preview/`, and records "
              "`review --status fact-checked`, then `review --status approved`, with their own name.",
              "2. `publish --batch " + args.batch + " --dry-run`, then `publish`. Pages that link to unpublished "
              "pages are held back automatically.",
              "3. Inspect the diff, commit and deploy.", ""]
    os.makedirs(BATCHES_DIR, exist_ok=True)
    out = os.path.join(BATCHES_DIR, f"{args.batch}-report.md")
    write(out, "\n".join(lines) + "\n")
    print(f"wrote {os.path.relpath(out, ROOT)}")
    return 0


CLAIM_FIELDS = ["claim_id", "claim_hash", "page", "claim", "source_url", "locator", "supporting_passage",
                "agent_status", "reviewer_decision", "reviewer_name", "reviewer_note"]
DECISIONS = ("confirmed", "rejected")


def claims_csv(batch):
    return os.path.join(content_lib.CONTENT, "batches", f"{batch}-claims.csv")


def claim_rows(pid):
    """One row per claim in the draft. claim_hash ties a reviewer's decision to the exact claim."""
    if not os.path.exists(draft_path(pid)):
        return []
    meta = parse_draft(read(draft_path(pid)))[0]
    urls = {s.get("id"): s.get("url", "") for s in meta.get("sources", [])}
    rows = []
    for n, c in enumerate(meta.get("claims", []), 1):
        key = json.dumps([c.get("text"), c.get("source"), c.get("locator")], ensure_ascii=False)
        agent = ("text-matched by the drafting agent (not a fact-check)" if c.get("agent_check") == "matched"
                 else "UNRESOLVED: " + (c.get("unresolved") or "not checked against a primary source"))
        rows.append({"claim_id": f"{pid}#{n}", "claim_hash": sha(key), "page": pid, "claim": c.get("text", ""),
                     "source_url": urls.get(c.get("source"), ""), "locator": c.get("locator", ""),
                     "supporting_passage": c.get("passage", ""), "agent_status": agent,
                     "reviewer_decision": "", "reviewer_name": "", "reviewer_note": ""})
    return rows


def read_claims(batch):
    path = claims_csv(batch)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return {r["claim_id"]: r for r in csv.DictReader(fh)}


def write_claims(batch, ids):
    """Rebuild the sheet from the drafts, keeping each reviewer decision whose claim is unchanged."""
    old = read_claims(batch)
    rows, kept, cleared = [], 0, 0
    for pid in ids:
        for r in claim_rows(pid):
            prev = old.get(r["claim_id"])
            if prev and prev.get("reviewer_decision"):
                if prev.get("claim_hash") == r["claim_hash"]:
                    for k in ("reviewer_decision", "reviewer_name", "reviewer_note"):
                        r[k] = prev.get(k, "")
                    kept += 1
                else:
                    cleared += 1
            rows.append(r)
    path = claims_csv(batch)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, CLAIM_FIELDS)
        w.writeheader()
        w.writerows(rows)
    return rows, kept, cleared


def claim_gate(state, pid):
    """None if a person has confirmed every claim of the page as it stands now, else the reason."""
    batch = next((b for b, v in state["batches"].items() if pid in v["ids"]), None)
    current = claim_rows(pid)
    if not current:
        return None
    sheet = read_claims(batch) if batch else {}
    problems = []
    for r in current:
        got = sheet.get(r["claim_id"])
        if not got or got.get("claim_hash") != r["claim_hash"]:
            problems.append(f"{r['claim_id']}: not in the claims sheet as it now reads; run `claims --batch {batch}`")
        elif got.get("reviewer_decision", "").strip().lower() not in DECISIONS or not got.get("reviewer_name", "").strip():
            problems.append(f"{r['claim_id']}: no reviewer decision (confirmed / rejected) and reviewer name")
        elif got["reviewer_decision"].strip().lower() == "rejected":
            problems.append(f"{r['claim_id']}: rejected by {got['reviewer_name']}; fix or remove the claim first")
    return "; ".join(problems) or None


def cmd_claims(args):
    state = load_state()
    rows, kept, cleared = write_claims(args.batch, batch_ids(state, args.batch))
    unresolved = sum(r["agent_status"].startswith("UNRESOLVED") for r in rows)
    print(f"wrote {os.path.relpath(claims_csv(args.batch), ROOT)}: {len(rows)} claims ({unresolved} unresolved), "
          f"{kept} reviewer decisions kept, {cleared} cleared because the claim changed")
    return 0


def cmd_review(args):
    state = load_state()
    topics = topics_by_id()
    pid = args.id
    if pid not in topics:
        sys.exit(f"unknown id {pid}")
    if not args.reviewer.strip():
        sys.exit("--reviewer must name the person who reviewed the page")
    ps = page_state(state, pid)
    run_validation(state, [pid], topics)
    if args.status in ("fact-checked", "approved") and ps.get("errors"):
        sys.exit(f"{pid} fails automated validation; fix the draft first")
    if args.status == "approved" and ps["status"] not in ("fact-checked", "approved") and not args.with_fact_check:
        sys.exit("approve needs a prior fact-check; pass --with-fact-check if this review also checked every claim")
    if args.status in ("fact-checked", "approved"):
        blocked = claim_gate(state, pid)
        if blocked:
            sys.exit(f"{pid}: every claim needs a reviewer decision in the claims sheet first: {blocked}")
    review = {"status": args.status, "reviewer": args.reviewer.strip(), "date": date.today().isoformat(),
              "scope": args.scope or "", "note": args.note or ""}
    ps["review"] = review
    ps["reviewed_hash"] = ps["draft_hash"]
    set_status(state, pid, "rejected" if args.status == "rejected" else args.status,
               f"{args.status} by {review['reviewer']}: {args.note or ''}".strip())
    save_state(state)
    print(f"{pid}: {ps['status']}")
    return 0


def replace_block(text, inner, anchor_patterns):
    """Insert or update the marked pipeline block. Returns the new text."""
    nl = "\r\n" if "\r\n" in text else "\n"
    block = BLOCK_START + nl + inner.replace("\n", nl) + nl + BLOCK_END
    if BLOCK_START in text:
        return re.sub(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END), lambda _m: block, text, flags=re.S)
    for pat in anchor_patterns:
        m = re.search(pat, text)
        if m:
            return text[:m.start()] + block + nl + text[m.start():]
    raise ValueError("no anchor for the link block")


def links_block(from_path, pages, heading):
    items = "\n".join(f'        <li><a href="{rel(from_path, p)}">{esc(t)}</a></li>' for p, t in pages)
    return (f'<div class="content-box" style="margin:1.5rem 0">\n    <h2 style="font-size:1.15rem">{esc(heading)}</h2>\n'
            f'    <ul class="bullet-list">\n{items}\n    </ul>\n</div>')


def guarded_write(state, path, text, pending):
    """Stage a pipeline-managed file unless someone edited it by hand since the last publish."""
    full = os.path.join(ROOT, path)
    current = file_hash(full)
    if current is not None and state.get("managed_files", {}).get(path) != current:
        return f"REFUSED  {path}: not written by the pipeline, or changed by hand since"
    if current is not None and read(full) == text:
        return f"same     {path}"
    pending[path] = (text, "file")
    return f"stage    {path}"


def site_html():
    """Site-relative paths of the HTML pages on disk (tooling and content folders excluded)."""
    skip = {".git", ".vscode", "node_modules", "scripts", "search console", "content", "tests"}
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.endswith(".html"):
                yield os.path.relpath(os.path.join(base, f), ROOT).replace(os.sep, "/")


def release_problems(pending, new_paths):
    """Check the site as it would be after this release: no broken internal links in any
    staged file, and every new page or hub reachable by links from the home page."""
    def exists(p):
        return p in pending or os.path.exists(os.path.join(ROOT, p))

    def text_of(p):
        return pending[p][0] if p in pending else read(os.path.join(ROOT, p))

    def targets(path, text):
        return {tgt for href in re.findall(r'href="([^"]+)"', text)
                for tgt in [resolve_link(href, path)] if tgt}

    problems = []
    for path, (text, _kind) in sorted(pending.items()):
        for tgt in sorted(targets(path, text)):
            if not exists(tgt):
                problems.append(f"{path}: broken internal link to {tgt}")
    pages = set(site_html()) | set(pending)
    seen, todo = set(), ["index.html"]
    while todo:
        path = todo.pop()
        if path in seen or path not in pages:
            continue
        seen.add(path)
        todo += [tgt for tgt in targets(path, text_of(path)) if tgt.endswith(".html")]
    for path in sorted(new_paths):
        if path not in seen:
            problems.append(f"{path}: orphan (not reachable by links from the home page)")
    return problems


def cmd_publish(args):
    state = load_state()
    topics = topics_by_id()
    ids = batch_ids(state, args.batch)
    run_validation(state, ids, topics)
    today = date.today().isoformat()
    published, log, candidates = [], [], []
    for pid in ids:
        ps = page_state(state, pid)
        t = topics[pid]
        if ps["status"] not in ("approved", "published"):
            log.append(f"skip     {pid}: status {ps['status']} (only approved pages are published)")
            continue
        if ps.get("reviewed_hash") != ps.get("draft_hash"):
            log.append(f"skip     {pid}: draft changed after approval")
            continue
        full = os.path.join(ROOT, t["path"])
        if os.path.exists(full) and file_hash(full) != ps.get("published_hash"):
            log.append(f"REFUSED  {t['path']}: exists and was not written by this pipeline (or edited by hand)")
            continue
        first = ps.get("date_published") or today
        review = dict(ps["review"], status="published")
        html = render(read(draft_path(pid)), t, review=review, date_published=first, date_modified=today,
                      related_links=related_for(pid, topics, state))
        candidates.append((pid, t, html, full, first))

    # A page may only link to pages that exist or are published in this run (plus hubs created here).
    while True:
        will_exist = {c[1]["path"] for c in candidates} | {hub_for(c[1]["folder"]) for c in candidates
                                                            if c[1]["folder"] in NEW_HUBS}
        dropped = []
        for c in candidates:
            missing = sorted({tgt for href in re.findall(r'href="([^"]+)"', c[2])
                              for tgt in [resolve_link(href, c[1]["path"])]
                              if tgt and not os.path.exists(os.path.join(ROOT, tgt)) and tgt not in will_exist})
            if missing:
                dropped.append(c)
                log.append(f"skip     {c[0]}: links to pages that are not published: {', '.join(missing)}")
        if not dropped:
            break
        candidates = [c for c in candidates if c not in dropped]

    # Every write is staged first and applied only if the whole release checks out.
    pending, staged = {}, []
    for pid, t, html, full, first in candidates:
        published.append(pid)
        if os.path.exists(full) and parse_body(read(full)) == parse_body(html):
            log.append(f"same     {t['path']}")
            continue
        pending[t["path"]] = (html, "file")
        staged.append((pid, t, html, first))
        log.append(f"{'would publish' if args.dry_run else 'publish'}  {t['path']}")

    # Hubs and parent-page link blocks are rebuilt from everything published so far.
    all_pub = [topics[p] for p, s in state["pages"].items() if s.get("status") == "published" and p in topics]
    all_pub += [topics[p] for p in published if topics[p] not in all_pub]
    by_folder = {}
    for t in all_pub:
        by_folder.setdefault(t["folder"], []).append(t)
    new_paths = {t["path"] for _pid, t, _h, _f in staged}
    for folder, pages in sorted(by_folder.items()):
        hub = hub_for(folder)
        items = [(p["path"], p["title"], p["learning_outcome"]) for p in pages]
        if folder in NEW_HUBS and (not os.path.exists(os.path.join(ROOT, hub)) or hub in state.get("managed_files", {})):
            if not os.path.exists(os.path.join(ROOT, hub)):
                new_paths.add(hub)
            title, intro = NEW_HUBS[folder]
            log.append(guarded_write(state, hub, hub_page(folder, title, intro, items,
                                                           "Study Notes" if folder.startswith("study/") else "Home"),
                                     pending))
        else:
            log.append(update_block(state, hub, links_block(hub, [(p, ti) for p, ti, _ in items], "New in-depth pages"),
                                    args.dry_run, pending))
    parents = {}
    for t in all_pub:
        for p in parents_for(t):
            if os.path.exists(os.path.join(ROOT, p)):
                parents.setdefault(p, []).append((t["path"], t["title"]))
    for p, links in sorted(parents.items()):
        log.append(update_block(state, p, links_block(p, links, "Go deeper on this topic"), args.dry_run, pending))
    new_hubs = [(hub_for(f), NEW_HUBS[f][0]) for f in sorted(by_folder) if f in NEW_HUBS]
    if new_hubs:
        log.append(update_block(state, "study/index.html", links_block("study/index.html", new_hubs, "More subjects"),
                                args.dry_run, pending))

    problems = release_problems(pending, new_paths)
    log += [f"REFUSED  {p}" for p in problems]
    refused = any(line.startswith("REFUSED") for line in log)
    for line in log:
        print(line)
    if refused:
        print("nothing was written: fix the refusals above and run publish again")
        return 1
    if args.dry_run:
        print(f"dry run: {len(pending)} file(s) would be written; release checks passed")
        return 0

    for path, (text, kind) in sorted(pending.items()):
        write(os.path.join(ROOT, path), text)
        if kind == "block":
            m = re.search(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END), text, re.S)
            state.setdefault("managed_blocks", {})[path] = sha(m.group(0).replace("\r\n", "\n"))
        else:
            state.setdefault("managed_files", {})[path] = sha(text)
    for pid, t, html, first in staged:
        ps = page_state(state, pid)
        ps["published_hash"] = sha(html)
        ps["date_published"] = first
        if ps["status"] != "published":
            set_status(state, pid, "published", f"published by pipeline on {today}")
    for line in apply_series(state, topics, False):
        print(line)
    save_state(state)
    print(f"wrote {len(pending)} file(s)")
    if staged and not args.no_site_checks:
        for script in ("build_sitemap.py", "seo_check.py"):
            res = subprocess.run([sys.executable, "-X", "utf8", os.path.join(ROOT, "scripts", script)],
                                 capture_output=True, text=True, encoding="utf-8")
            print(res.stdout.strip().splitlines()[-1] if res.stdout.strip() else res.stderr[-300:])
            if res.returncode != 0:
                print(f"{script} failed; inspect before committing")
                return 1
    return 0


def parse_body(html):
    """Page text minus the modified dates and the prev/next bar (rewritten by `series`),
    to detect publishes that change nothing."""
    return NAV_RE.sub("", re.sub(r'"dateModified": "[^"]*"|Last updated: [^<]*', "", html))


def series_order(state, topics):
    """Published pipeline pages per folder, in the order their hub lists them."""
    by_folder = {}
    for pid, ps in state["pages"].items():
        if ps.get("status") == "published" and pid in topics:
            by_folder.setdefault(topics[pid]["folder"], []).append(topics[pid]["path"])
    out = {}
    for folder, paths in by_folder.items():
        hub = hub_for(folder)
        listed = []
        if os.path.exists(os.path.join(ROOT, hub)):
            for href in re.findall(r'href="([^"]+)"', read(os.path.join(ROOT, hub))):
                tgt = resolve_link(href, hub)
                if tgt in paths and tgt not in listed:
                    listed.append(tgt)
        out[folder] = listed + sorted(set(paths) - set(listed))
    return out


def series_nav(path, prev, nxt):
    """The prev / hub / next bar at the foot of a pipeline page."""
    folder = os.path.dirname(path)
    hub_name = HUB_NAMES.get(folder, folder.split("/")[-1].title())
    hub_label = ("↑ " if prev and nxt else "← " if nxt else "") + esc(hub_name) + (" →" if prev and not nxt else "")
    links = []
    if prev:
        links.append(f'<a href="{rel(path, prev)}" class="nav-btn">← {esc(title_of(prev))}</a>')
    links.append(f'<a href="index.html" class="nav-btn">{hub_label}</a>')
    if nxt:
        links.append(f'<a href="{rel(path, nxt)}" class="nav-btn">{esc(title_of(nxt))} →</a>')
    return '<div class="page-navigation">\n' + "\n".join("            " + a for a in links) + "\n        </div>"


def apply_series(state, topics, dry):
    """Point every published pipeline page at its neighbours in hub order. Only the
    navigation bar changes, and only while it holds nothing but pipeline links. A page
    changed since publishing keeps its old hash, so `publish` still refuses to overwrite it."""
    log = []
    pid_of = {t["path"]: pid for pid, t in topics.items()}
    for _folder, paths in sorted(series_order(state, topics).items()):
        for i, path in enumerate(paths):
            full = os.path.join(ROOT, path)
            ps = page_state(state, pid_of[path])
            if not os.path.exists(full):
                continue
            text = read(full)
            m = NAV_RE.search(text)
            if not m or re.sub(r'\s*<a href="[a-z0-9-]+\.html" class="nav-btn">[^<]*</a>', "",
                               m.group(0)).split() != ['<div', 'class="page-navigation">', '</div>']:
                log.append(f"REFUSED  {path}: navigation bar missing or edited by hand")
                continue
            matched = file_hash(full) == ps.get("published_hash")
            nl = "\r\n" if "\r\n" in text else "\n"
            nav = series_nav(path, paths[i - 1] if i else None, paths[i + 1] if i + 1 < len(paths) else None)
            new = NAV_RE.sub(lambda _m: nav.replace("\n", nl), text, count=1)
            if new == text:
                continue
            if not dry:
                write(full, new)
                if matched:
                    if state.get("managed_files", {}).get(path) == ps["published_hash"]:
                        state["managed_files"][path] = sha(new)
                    ps["published_hash"] = sha(new)
            log.append(f"{'would link' if dry else 'linked'}   {path}")
    return log


def cmd_series(args):
    state = load_state()
    log = apply_series(state, topics_by_id(), args.dry_run)
    for line in log:
        print(line)
    if not args.dry_run:
        save_state(state)
    done = sum(1 for line in log if not line.startswith("REFUSED"))
    print(f"{done} page(s) {'would be ' if args.dry_run else ''}relinked")
    return 1 if any(line.startswith("REFUSED") for line in log) else 0


def update_block(state, path, inner, dry, pending=None):
    """Insert or refresh the pipeline link block in an existing page. With `pending`, the
    new text is staged there instead of written."""
    full = os.path.join(ROOT, path)
    if pending is not None and path in pending:
        return f"REFUSED  {path}: would get two pipeline link blocks in one run"
    if not os.path.exists(full):
        return f"skip     {path}: does not exist"
    text = read(full)
    try:
        new = replace_block(text, inner, [r'[ \t]*<div class="page-navigation">', r"[ \t]*</section>\s*</main>",
                                          r"[ \t]*</main>"])
    except ValueError as exc:
        return f"REFUSED  {path}: {exc}"
    if new == text:
        return f"same     {path}"
    blocks = state.setdefault("managed_blocks", {})
    m = re.search(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END), text, re.S)
    if m and blocks.get(path) != sha(m.group(0).replace("\r\n", "\n")):
        return f"REFUSED  {path}: the pipeline link block was edited by hand"
    if pending is not None:
        pending[path] = (new, "block")
        return f"{'would update' if dry else 'update'}  {path} (pipeline link block only)"
    if not dry:
        write(full, new)
        m = re.search(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END), new, re.S)
        blocks[path] = sha(m.group(0).replace("\r\n", "\n"))
    return f"{'would update' if dry else 'updated'}  {path} (pipeline link block only)"


def cmd_status(_args):
    state = load_state()
    topics = topics_by_id()
    counts = {}
    for t in topics.values():
        st = page_state(state, t["id"])["status"]
        counts[st] = counts.get(st, 0) + 1
    print("new pages by status:", counts)
    for name, b in state["batches"].items():
        sts = [page_state(state, i)["status"] for i in b["ids"]]
        print(f"{name} ({b['created']}): " + ", ".join(f"{s} {sts.count(s)}" for s in sorted(set(sts))))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    s = sub.add_parser("select")
    s.add_argument("--batch-size", type=int, default=20)
    s.add_argument("--ids")
    s.add_argument("--category", choices=list(CATEGORIES))
    s.add_argument("--priority", choices=list(PRIORITY_ORDER))
    for name in ("scaffold", "validate", "render", "report", "claims", "publish"):
        p = sub.add_parser(name)
        p.add_argument("--batch", required=True)
        if name == "validate":
            p.add_argument("--verbose", action="store_true")
        if name == "publish":
            p.add_argument("--dry-run", action="store_true")
            p.add_argument("--no-site-checks", action="store_true", help="skip sitemap rebuild and seo_check (tests only)")
    r = sub.add_parser("review")
    r.add_argument("--id", required=True)
    r.add_argument("--status", required=True, choices=["fact-checked", "approved", "rejected"])
    r.add_argument("--reviewer", required=True)
    r.add_argument("--scope")
    r.add_argument("--note")
    r.add_argument("--with-fact-check", action="store_true")
    sub.add_parser("status")
    s = sub.add_parser("series", help="refresh the prev/next bar on published pages")
    s.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    return globals()["cmd_" + args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
