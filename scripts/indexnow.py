"""Tell IndexNow search engines (Bing, Yandex, Seznam, Naver) which pages changed.

Google does not use IndexNow; it reads sitemap.xml via Search Console.

Only indexable pages (the ones build_sitemap.py lists) are submitted. The key
is public by design: it lives in /<key>.txt at the site root, and the script
checks that file is live before sending anything.

Usage:
  python scripts/indexnow.py --init              create the key file (once)
  python scripts/indexnow.py --since <git-rev>   list pages changed since <git-rev>
  python scripts/indexnow.py --all               list every indexable page
  add --send to actually submit (the default only prints the URLs)
"""
import argparse
import glob
import json
import os
import re
import secrets
import subprocess
import sys
import urllib.error
import urllib.request

from seo_lib import HOST, ROOT, html_pages, is_indexable, soup_for, url_for

ENDPOINT = "https://api.indexnow.org/indexnow"
KEY_RE = re.compile(r"^[0-9a-f]{32}$")


def find_key():
    keys = []
    for path in glob.glob(os.path.join(ROOT, "*.txt")):
        name = os.path.splitext(os.path.basename(path))[0]
        if KEY_RE.match(name):
            with open(path, encoding="utf-8") as fh:
                if fh.read().strip() == name:
                    keys.append(name)
    if len(keys) > 1:
        sys.exit(f"more than one IndexNow key file at the site root: {keys}")
    return keys[0] if keys else None


def init_key():
    key = find_key()
    if key:
        print(f"key already exists: {key}.txt")
        return
    key = secrets.token_hex(16)
    with open(os.path.join(ROOT, f"{key}.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(key + "\n")
    print(f"created {key}.txt; commit and deploy it before using --send")


def changed_pages(since):
    out = subprocess.run(["git", "diff", "--name-only", "--diff-filter=AM", since, "HEAD", "--", "*.html"],
                         cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return {p.strip() for p in out.splitlines() if p.strip()}


def select_urls(only=None):
    """Indexable page URLs, optionally limited to the repo-relative paths in `only`."""
    urls = []
    for rel in html_pages():
        if only is not None and rel not in only:
            continue
        if is_indexable(rel, soup_for(rel)):
            urls.append(url_for(rel))
    return sorted(urls)


def key_is_live(key):
    try:
        with urllib.request.urlopen(f"{HOST}/{key}.txt", timeout=20) as resp:
            return resp.status == 200 and resp.read().decode("utf-8").strip() == key
    except urllib.error.URLError:
        return False


def submit(key, urls):
    body = json.dumps({
        "host": HOST.split("://", 1)[1],
        "key": key,
        "keyLocation": f"{HOST}/{key}.txt",
        "urlList": urls,
    }).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--init", action="store_true", help="create the key file")
    group.add_argument("--since", metavar="GIT_REV", help="pages added or changed since this commit")
    group.add_argument("--all", action="store_true", help="every indexable page")
    ap.add_argument("--send", action="store_true", help="submit to IndexNow (default: print only)")
    args = ap.parse_args()

    if args.init:
        init_key()
        return

    urls = select_urls(changed_pages(args.since) if args.since else None)
    for url in urls:
        print(url)
    print(f"{len(urls)} URL(s)")
    if not args.send or not urls:
        if urls:
            print("dry run: add --send to submit")
        return

    key = find_key()
    if not key:
        sys.exit("no key file; run --init, then commit and deploy it")
    if not key_is_live(key):
        sys.exit(f"{HOST}/{key}.txt is not live yet; deploy it before sending")
    status = submit(key, urls[:10000])
    # 200 = accepted, 202 = received (key check pending); anything else is a failure.
    print(f"IndexNow responded {status}")
    if status not in (200, 202):
        sys.exit(1)


if __name__ == "__main__":
    main()
