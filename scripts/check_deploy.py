"""After a deploy, confirm the live site does not serve pipeline files.

Each path must return 404, or, if Vercel served it anyway, carry an
X-Robots-Tag noindex header (the vercel.json fallback). Read-only GETs.

Usage: python scripts/check_deploy.py [--host https://www.aspirantdaily.com]
"""
import argparse
import sys
import urllib.error
import urllib.request

PATHS = ["content/state.json", "content/drafts/successive-discount-formula.html",
         "content/preview/study/quant/index.html", "scripts/seo_lib.py", "scripts/content_pipeline.py",
         "tests/test_site.py", "CONTENT_MASTER_PLAN.csv", "CONTENT_MASTER_PLAN.md", "content_inventory.json"]


def status(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=20) as res:
            return res.status, res.headers.get("X-Robots-Tag", "")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("X-Robots-Tag", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="https://www.aspirantdaily.com")
    host = ap.parse_args().host.rstrip("/")
    bad = 0
    for path in PATHS:
        code, robots = status(f"{host}/{path}")
        if code == 404:
            verdict = "ok (not deployed)"
        elif "noindex" in robots:
            verdict = "WARN served, but noindex"
        else:
            verdict = "FAIL served and indexable"
            bad += 1
        print(f"{code}  {verdict:28} /{path}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
