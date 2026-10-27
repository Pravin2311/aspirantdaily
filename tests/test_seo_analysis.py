import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "seo"))
from analysis import gsc_page_regex  # noqa: E402


class GscPageRegexTest(unittest.TestCase):
    """Search Console filters on full URLs; experiment regexes are written against paths."""

    def matches(self, path_regex, url):
        return bool(re.search(gsc_page_regex(path_regex), url))

    def test_anchored_path_matches_full_url_on_www_and_apex(self):
        for url in ("https://www.aspirantdaily.com/exam-calendar.html", "https://aspirantdaily.com/exam-calendar.html"):
            self.assertTrue(self.matches(r"^/exam-calendar\.html$", url))

    def test_home_regex_matches_only_the_home_page(self):
        self.assertTrue(self.matches(r"^/$", "https://www.aspirantdaily.com/"))
        self.assertFalse(self.matches(r"^/$", "https://www.aspirantdaily.com/about.html"))

    def test_anchor_still_excludes_other_paths(self):
        self.assertFalse(self.matches(r"^/exam-calendar\.html$", "https://www.aspirantdaily.com/blog/exam-calendar.html"))

    def test_unanchored_regex_is_unchanged(self):
        self.assertEqual(gsc_page_regex(".*"), ".*")
        self.assertEqual(gsc_page_regex("/study/current-affairs/x"), "/study/current-affairs/x")


if __name__ == "__main__":
    unittest.main()
