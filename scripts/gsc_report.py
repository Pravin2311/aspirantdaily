"""Summarise Google Search Console exports against the current site.

Coverage: point it at a folder containing Page-indexing "Coverage-Drilldown"
exports (each subfolder has Metadata.csv and Table.csv). Every reported URL is
classified against the site as it is now: is it the canonical www URL, is it
in sitemap.xml, does the file exist.

Performance (optional): pass --pages and/or --queries with the Pages.csv /
Queries.csv files from a Performance export, and --prev-pages / --prev-queries
with the same export for the preceding period to get period-over-period
changes. Columns expected: first column (page or query), Clicks, Impressions,
CTR, Position.

Usage:
  python scripts/gsc_report.py "search console"
  python scripts/gsc_report.py "search console" --pages cur/Pages.csv --prev-pages prev/Pages.csv
"""
import argparse
import csv
import glob
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
from urllib.parse import urlparse

from seo_lib import HOST, ROOT


def sitemap_urls():
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(os.path.join(ROOT, "sitemap.xml")).getroot()
    return {loc.text.strip() for loc in root.findall(".//s:loc", ns)}


def classify(url, listed):
    p = urlparse(url)
    path = p.path + ("index.html" if p.path.endswith("/") else "")
    exists = os.path.exists(os.path.join(ROOT, path.lstrip("/")))
    if p.scheme != "https" or p.netloc != "www.aspirantdaily.com":
        return "non-canonical host/protocol (expected to redirect)"
    if p.query:
        return "URL with query string"
    if url in listed:
        return "canonical, in sitemap"
    if not exists:
        return "no such page now (404)"
    return "exists, not in sitemap (noindex or alias)"


def coverage(folder):
    listed = sitemap_urls()
    for sub in sorted(glob.glob(os.path.join(folder, "*", ""))):
        meta_path, table_path = os.path.join(sub, "Metadata.csv"), os.path.join(sub, "Table.csv")
        if not (os.path.exists(meta_path) and os.path.exists(table_path)):
            continue
        with open(meta_path, encoding="utf-8-sig") as fh:
            meta = {row[0]: row[1] for row in csv.reader(fh) if len(row) >= 2}
        with open(table_path, encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        groups = defaultdict(list)
        for row in rows:
            groups[classify(row["URL"], listed)].append(row)
        print(f"\n## {meta.get('Issue', os.path.basename(sub.rstrip(os.sep)))} ({len(rows)} URLs in sample)")
        for label, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            print(f"  {len(items):3d}  {label}")
            for row in items[:5]:
                print(f"         {row['URL']}  (last crawled {row.get('Last crawled', '?')})")


def load_perf(path):
    if not path:
        return {}
    with open(path, encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        idx = {name.strip().lower(): i for i, name in enumerate(header)}
        out = {}
        for row in reader:
            def num(col):
                v = row[idx[col]].replace("%", "").replace(",", "").strip()
                return float(v) if v else 0.0
            out[row[0]] = dict(clicks=num("clicks"), impressions=num("impressions"),
                               ctr=num("ctr"), position=num("position"))
        return out


def performance(label, cur_path, prev_path):
    cur, prev = load_perf(cur_path), load_perf(prev_path)
    if not cur:
        return
    print(f"\n## {label}: {len(cur)} rows, {sum(r['clicks'] for r in cur.values()):.0f} clicks, "
          f"{sum(r['impressions'] for r in cur.values()):.0f} impressions")
    near = [(k, r) for k, r in cur.items() if 8 <= r["position"] <= 20 and r["impressions"] >= 20]
    print("\n  Near page one (position 8-20, >=20 impressions):")
    for k, r in sorted(near, key=lambda kv: -kv[1]["impressions"])[:20]:
        print(f"    pos {r['position']:5.1f}  impr {r['impressions']:6.0f}  {k}")
    low_ctr = [(k, r) for k, r in cur.items() if r["impressions"] >= 100 and r["ctr"] < 1.0]
    print("\n  Low CTR (>=100 impressions, CTR < 1%):")
    for k, r in sorted(low_ctr, key=lambda kv: -kv[1]["impressions"])[:20]:
        print(f"    ctr {r['ctr']:4.1f}%  impr {r['impressions']:6.0f}  pos {r['position']:5.1f}  {k}")
    if prev:
        deltas = []
        for k in set(cur) | set(prev):
            c, p = cur.get(k, {}), prev.get(k, {})
            deltas.append((c.get("clicks", 0) - p.get("clicks", 0),
                           c.get("impressions", 0) - p.get("impressions", 0), k))
        print("\n  Biggest losers vs previous period (clicks, impressions):")
        for dc, di, k in sorted(deltas)[:15]:
            print(f"    {dc:+6.0f}  {di:+8.0f}  {k}")
        print("\n  Biggest gainers:")
        for dc, di, k in sorted(deltas, reverse=True)[:15]:
            print(f"    {dc:+6.0f}  {di:+8.0f}  {k}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", nargs="?", help="folder with Coverage-Drilldown exports")
    ap.add_argument("--pages"), ap.add_argument("--prev-pages")
    ap.add_argument("--queries"), ap.add_argument("--prev-queries")
    args = ap.parse_args()
    print(f"# Search Console report (site: {HOST})")
    if args.folder:
        coverage(args.folder)
    performance("Pages", args.pages, args.prev_pages)
    performance("Queries", args.queries, args.prev_queries)


if __name__ == "__main__":
    main()
