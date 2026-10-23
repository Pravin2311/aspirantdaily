"""Regression tests for the live site: routes, SEO fixes and data files.

Run: python -X utf8 -m unittest discover -s tests -v
"""
import glob
import json
import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from seo_lib import HOST, canonical_of, html_pages, is_indexable, soup_for, url_for  # noqa: E402

KEY_ROUTES = [
    "index.html", "study/index.html", "blog/index.html", "repeated-questions/index.html", "exam-calendar.html",
    "quiz.html", "quiz-selector.html", "contact.html", "privacy-policy.html", "terms.html",
    "blog/upsc-prelims-syllabus-2025.html", "blog/ssc-cgl-syllabus-2025.html",
    "blog/how-to-score-180-ssc-cgl-tier1.html", "study/polity/parliament-of-india.html",
]


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


class SiteTests(unittest.TestCase):
    def test_seo_check_passes(self):
        res = subprocess.run([sys.executable, "-X", "utf8", os.path.join(ROOT, "scripts", "seo_check.py")],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(res.returncode, 0, res.stdout[-2000:])

    def test_index_html_redirect(self):
        cfg = json.loads(read("vercel.json"))
        self.assertIn({"source": "/index.html", "destination": "/", "permanent": True}, cfg["redirects"])

    def test_robots_points_to_www_sitemap(self):
        robots = read("robots.txt")
        self.assertIn(f"Sitemap: {HOST}/sitemap.xml", robots)
        self.assertNotRegex(robots, r"(?m)^Disallow:\s*/\s*$")

    def test_sitemap_uses_www_and_matches_pages(self):
        locs = re.findall(r"<loc>([^<]+)</loc>", read("sitemap.xml"))
        self.assertTrue(locs)
        self.assertTrue(all(loc.startswith(HOST + "/") or loc == HOST + "/" for loc in locs))
        indexable = {url_for(p) for p in html_pages() if is_indexable(p, soup_for(p))}
        self.assertEqual(set(locs), indexable)

    def test_canonicals_self_reference_www(self):
        for rel in html_pages():
            soup = soup_for(rel)
            if is_indexable(rel, soup):
                self.assertEqual(canonical_of(soup), [url_for(rel)], rel)

    def test_key_routes_exist(self):
        for rel in KEY_ROUTES:
            self.assertTrue(os.path.exists(os.path.join(ROOT, rel)), rel)

    def test_quiz_answers_are_options(self):
        for path in glob.glob(os.path.join(ROOT, "data", "*.json")):
            with open(path, encoding="utf-8") as fh:
                questions = json.load(fh)["questions"]
            for i, q in enumerate(questions):
                for lang in q["options"]:
                    self.assertIn(q["answer"][lang], q["options"][lang], f"{os.path.basename(path)} #{i} ({lang})")

    def test_no_unsupported_trust_claims(self):
        pattern = re.compile(r"facts checked|fact-checked by|guaranteed (marks|selection)|all facts verified", re.I)
        for rel in html_pages():
            self.assertIsNone(pattern.search(read(rel)), rel)

    def test_pipeline_files_not_deployed(self):
        ignore = read(".vercelignore").split()
        for entry in ("/content", "/scripts", "/tests", "/*.md"):
            self.assertIn(entry, ignore)

    def test_pipeline_paths_are_noindex_if_ever_served(self):
        # Second layer behind .vercelignore: if those folders were ever deployed, they still are not indexed.
        with open(os.path.join(ROOT, "vercel.json"), encoding="utf-8") as fh:
            headers = {h["source"]: h["headers"] for h in json.load(fh).get("headers", [])}
        for folder in ("content", "scripts", "tests"):
            self.assertIn({"key": "X-Robots-Tag", "value": "noindex, nofollow"}, headers.get(f"/{folder}/:path*", []))

    def test_drafts_are_noindex_and_never_in_sitemap(self):
        with open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8") as fh:
            sitemap = fh.read()
        self.assertNotIn("/content/", sitemap)
        for path in glob.glob(os.path.join(ROOT, "content", "preview", "**", "*.html"), recursive=True):
            with open(path, encoding="utf-8") as fh:
                self.assertIn('<meta name="robots" content="noindex, nofollow">', fh.read(), path)

    def test_previews_are_not_in_site_scan(self):
        self.assertFalse(any(p.startswith("content/") for p in html_pages()))

    def test_indexnow_key_and_urls(self):
        import indexnow
        key = indexnow.find_key()
        self.assertIsNotNone(key, "IndexNow key file missing at the site root")
        urls = indexnow.select_urls()
        sitemap = re.findall(r"<loc>([^<]+)</loc>", read("sitemap.xml"))
        self.assertEqual(sorted(urls), sorted(sitemap))
        self.assertEqual(indexnow.select_urls({"quiz.html"}), [])  # noindex pages are never submitted


if __name__ == "__main__":
    unittest.main()
