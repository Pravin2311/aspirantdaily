"""
URL-inspects every sitemap URL through the Search Console API (read-only)
and saves the coverage state, last crawl and canonicals per URL, plus a
summary: how many URLs are indexed, by section, and how many Google has
canonicalised to the apex host instead of www.

Usage:
  seo\\.venv\\Scripts\\python seo\\inspect_all.py [--limit N]
  python seo\\inspect_all.py --summary [FILE]   # summarise a saved run; no API call

Writes seo/data/<today>/inspections-all.json (and -summary.json) and resumes
from it if a previous run today stopped part-way. Quota: 2,000 inspections
per day per property (600/minute); the weekly run uses ~30, so don't run
this more than once a day. Adapted from Teachings.ai/seo/inspect_all.py.
"""
import collections
import datetime as dt
import glob
import json
import os
import socket
import sys
import time
from urllib.parse import urlparse

# the Google client has no request timeout by default; one stalled connection hung a full run
socket.setdefaulttimeout(60)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import weekly  # noqa: E402


def section_of(url):
    """'/study/quant/x.html' -> '/study/quant/', '/blog/x.html' -> '/blog/', '/x.html' -> '/'."""
    parts = urlparse(url).path.strip("/").split("/")[:-1]
    if parts[:1] == ["study"]:
        parts = parts[:2]
    else:
        parts = parts[:1]
    return "/" + "".join(p + "/" for p in parts)


def summarize(results, site_origin):
    """Counts by coverage state and section, and URLs whose Google canonical is on another host."""
    live_host = urlparse(site_origin).netloc.lower()
    ok = [r for r in results if "error" not in r]
    by_state = collections.Counter(r.get("coverageState") or "unknown" for r in ok)
    sections = collections.defaultdict(lambda: [0, 0])
    other_host, other_url = [], []
    for r in ok:
        indexed = r.get("verdict") == "PASS"
        sec = sections[section_of(r["url"])]
        sec[0] += indexed
        sec[1] += 1
        gc = r.get("googleCanonical") or ""
        if gc and urlparse(gc).netloc.lower() != live_host:
            other_host.append(r["url"])
        elif gc and gc.rstrip("/") != r["url"].rstrip("/"):
            other_url.append({"url": r["url"], "googleCanonical": gc})
    indexed = sum(1 for r in ok if r.get("verdict") == "PASS")
    return {
        "inspected": len(ok),
        "errors": len(results) - len(ok),
        "indexed": indexed,
        "indexed_share": round(indexed / len(ok), 3) if ok else 0,
        "by_state": dict(by_state.most_common()),
        "by_section": {k: {"indexed": v[0], "total": v[1]} for k, v in sorted(sections.items())},
        "canonical_other_host": sorted(other_host),
        "canonical_other_url": other_url,
    }


def print_summary(s):
    print(f"Indexed (verdict PASS): {s['indexed']} of {s['inspected']} ({s['indexed_share']:.0%})"
          + (f"; {s['errors']} URLs could not be inspected" if s["errors"] else ""))
    for state, n in s["by_state"].items():
        print(f"  {n:4}  {state}")
    print("By section (indexed/total):")
    for sec, v in s["by_section"].items():
        print(f"  {v['indexed']:3}/{v['total']:<3} {sec}")
    if s["canonical_other_host"]:
        print(f"Google canonical on another host (usually the apex): {len(s['canonical_other_host'])}")
        for u in s["canonical_other_host"]:
            print(f"  {u}")
    if s["canonical_other_url"]:
        print(f"Google picked a different URL as canonical: {len(s['canonical_other_url'])}")
        for x in s["canonical_other_url"]:
            print(f"  {x['url']} -> {x['googleCanonical']}")


def latest_run():
    runs = sorted(glob.glob(os.path.join(weekly.DATA_DIR, "*", "inspections-all.json")))
    return runs[-1] if runs else None


def inspect_all(limit=None):
    import gapi
    cfg = weekly.load_config()
    gsc = gapi.SearchConsole(gapi.get_credentials())
    site = weekly.pick_gsc_site(gsc, cfg)
    urls = weekly.sitemap_urls()[:limit]
    out_dir = os.path.join(weekly.DATA_DIR, dt.date.today().isoformat())
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "inspections-all.json")
    results = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            results = [r for r in json.load(f) if "error" not in r]
    done = {r["url"] for r in results}
    todo = [u for u in urls if u not in done]
    print(f"{len(done)} already inspected today, {len(todo)} to go", flush=True)
    for i, u in enumerate(todo, 1):
        for attempt in range(3):
            try:
                results.append(gsc.inspect(site, u))
                break
            except (socket.timeout, TimeoutError, ConnectionError) as e:
                if attempt < 2:
                    time.sleep(10)
                    continue
                results.append({"url": u, "error": f"network: {e}"})
                break
            except gapi.HttpError as e:
                if getattr(e.resp, "status", None) == 429 and attempt < 2:
                    time.sleep(60)  # per-minute quota; wait and retry
                    continue
                results.append({"url": u, "error": gapi.explain_http_error(e)})
                break
        time.sleep(0.15)
        if i % 50 == 0:
            print(f"{i}/{len(todo)}", flush=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=1)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    print(f"Done: {len(results)} URLs -> {path}")
    return path


def main():
    cfg = weekly.load_config()
    if "--summary" in sys.argv:
        i = sys.argv.index("--summary")
        path = sys.argv[i + 1] if len(sys.argv) > i + 1 else latest_run()
        if not path:
            print("No saved run found under seo/data/*/inspections-all.json", file=sys.stderr)
            return 2
    else:
        limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
        path = inspect_all(limit)
    with open(path, encoding="utf-8") as f:
        s = summarize(json.load(f), cfg["site_origin"])
    s["source"] = os.path.relpath(path, weekly.ROOT)
    with open(path.replace(".json", "-summary.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, indent=1)
    print_summary(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
