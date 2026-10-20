"""Regenerate sitemap.xml from the pages on disk.

Only indexable pages are listed: no noindex robots meta, and a single
self-referencing canonical. <lastmod> is the date of the last git commit
that changed the page body (or today, for uncommitted body edits), so it
only moves when the content actually changes.

Usage: python scripts/build_sitemap.py
"""
import os

from seo_lib import ROOT, git_dates, html_pages, is_indexable, soup_for, url_for


def main():
    entries = []
    for rel in html_pages():
        if is_indexable(rel, soup_for(rel)):
            _, modified = git_dates(rel)
            entries.append((url_for(rel), modified))
    entries.sort(key=lambda e: (e[0] != url_for("index.html"), e[0]))

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, modified in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        if modified:
            lines.append(f"    <lastmod>{modified}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")

    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"sitemap.xml: {len(entries)} URLs")


if __name__ == "__main__":
    main()
