"""Static SEO checks for the site. Exits non-zero when an error is found.

Errors (fail the run):
  - broken internal links
  - indexable page without exactly one self-referencing canonical on the www host
  - og:url that differs from the canonical
  - missing <title>, meta description or <h1>; duplicate titles
  - invalid JSON-LD, or JSON-LD dates in the future
  - sitemap listing a missing / noindex / non-canonical URL, or omitting an
    indexable page; robots.txt not pointing at the www sitemap
Warnings (reported only): long titles, orphan pages, multiple <h1>.

Usage: python scripts/seo_check.py
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date
from urllib.parse import urljoin, urlparse

from seo_lib import HOST, ROOT, canonical_of, html_pages, is_indexable, robots_of, soup_for, url_for

SITE_HOSTS = {"www.aspirantdaily.com", "aspirantdaily.com"}
errors, warnings = [], []


def target_file(url):
    path = urlparse(url).path
    if path.endswith("/"):
        path += "index.html"
    return path.lstrip("/")


def check_jsonld(rel, soup):
    today = date.today().isoformat()
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except ValueError as exc:
            errors.append(f"{rel}: invalid JSON-LD ({exc})")
            continue
        for key, value in re.findall(r'"(date\w+)":\s*"([^"]+)"', json.dumps(data)):
            if value[:10] > today:
                errors.append(f"{rel}: JSON-LD {key} {value} is in the future")


def main():
    pages = list(html_pages())
    titles = defaultdict(list)
    inbound = Counter()
    indexable = set()

    for rel in pages:
        soup = soup_for(rel)
        url = url_for(rel)
        if is_indexable(rel, soup):
            indexable.add(url)
        elif "noindex" not in robots_of(soup):
            errors.append(f"{rel}: indexable but canonical is {canonical_of(soup)}, expected [{url}]")

        og_url = soup.find("meta", attrs={"property": "og:url"})
        canon = canonical_of(soup)
        if og_url and canon and og_url.get("content") != canon[0]:
            errors.append(f"{rel}: og:url {og_url.get('content')} differs from canonical {canon[0]}")

        title = soup.title.get_text(strip=True) if soup.title else ""
        if not title:
            errors.append(f"{rel}: missing <title>")
        titles[title].append(rel)
        if len(title) > 75:
            warnings.append(f"{rel}: title is {len(title)} chars")
        desc = soup.find("meta", attrs={"name": "description"})
        if not desc or not desc.get("content", "").strip():
            errors.append(f"{rel}: missing meta description")
        h1s = soup.find_all("h1")
        if not h1s:
            errors.append(f"{rel}: missing <h1>")
        elif len(h1s) > 1:
            warnings.append(f"{rel}: {len(h1s)} <h1> elements")
        check_jsonld(rel, soup)

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            absolute = urljoin(url, href)
            if urlparse(absolute).netloc not in SITE_HOSTS:
                continue
            dest = target_file(absolute)
            if os.path.exists(os.path.join(ROOT, dest)):
                if dest != rel:
                    inbound[dest] += 1
            else:
                errors.append(f"{rel}: broken link {href}")

    for title, rels in titles.items():
        if title and len(rels) > 1:
            errors.append(f"duplicate title {title!r}: {rels}")
    for rel in pages:
        if url_for(rel) in indexable and not inbound[rel] and rel != "index.html":
            warnings.append(f"{rel}: orphan (no internal links point here)")

    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(os.path.join(ROOT, "sitemap.xml")).getroot()
    listed = [loc.text.strip() for loc in root.findall(".//s:loc", ns)]
    for loc, n in Counter(listed).items():
        if n > 1:
            errors.append(f"sitemap: {loc} listed {n} times")
    for loc in listed:
        if not loc.startswith(HOST + "/"):
            errors.append(f"sitemap: {loc} is not on {HOST}")
        elif not os.path.exists(os.path.join(ROOT, target_file(loc))):
            errors.append(f"sitemap: {loc} has no file")
        elif loc not in indexable:
            errors.append(f"sitemap: {loc} is not indexable (noindex or non-self canonical)")
    for url in sorted(indexable - set(listed)):
        errors.append(f"sitemap: indexable page missing: {url}")

    with open(os.path.join(ROOT, "robots.txt"), encoding="utf-8") as fh:
        robots = fh.read()
    if f"Sitemap: {HOST}/sitemap.xml" not in robots:
        errors.append("robots.txt: missing Sitemap line for the www host")
    if re.search(r"^Disallow:\s*/\s*$", robots, re.M):
        errors.append("robots.txt: disallows the whole site")

    for w in warnings:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"\n{len(pages)} pages, {len(indexable)} indexable, {len(listed)} in sitemap: "
          f"{len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
