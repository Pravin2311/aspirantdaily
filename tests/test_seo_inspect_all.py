import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "seo"))
from inspect_all import section_of, summarize  # noqa: E402

SITE = "https://www.aspirantdaily.com"


def row(path, verdict="PASS", state="Submitted and indexed", canonical=None):
    url = SITE + path
    return {"url": url, "verdict": verdict, "coverageState": state,
            "googleCanonical": url if canonical is None else canonical, "userCanonical": url}


class SectionTest(unittest.TestCase):
    def test_study_pages_group_by_subject(self):
        self.assertEqual(section_of(SITE + "/study/quant/percentage-tricks.html"), "/study/quant/")
        self.assertEqual(section_of(SITE + "/study/quant/index.html"), "/study/quant/")

    def test_other_pages_group_by_top_folder(self):
        self.assertEqual(section_of(SITE + "/blog/rrb-syllabus-2025.html"), "/blog/")
        self.assertEqual(section_of(SITE + "/exam-calendar.html"), "/")
        self.assertEqual(section_of(SITE + "/"), "/")


class SummarizeTest(unittest.TestCase):
    def setUp(self):
        self.s = summarize([
            row("/"),
            row("/study/quant/a.html"),
            row("/study/quant/b.html", verdict="NEUTRAL", state="Discovered - currently not indexed", canonical=""),
            row("/blog/x.html", canonical="https://aspirantdaily.com/blog/x.html"),
            row("/study/polity/index.html", canonical=SITE + "/study/polity/"),
            {"url": SITE + "/blog/y.html", "error": "quota"},
        ], SITE)

    def test_counts_indexed_and_errors(self):
        self.assertEqual((self.s["inspected"], self.s["indexed"], self.s["errors"]), (5, 4, 1))
        self.assertEqual(self.s["by_state"]["Discovered - currently not indexed"], 1)

    def test_sections(self):
        self.assertEqual(self.s["by_section"]["/study/quant/"], {"indexed": 1, "total": 2})

    def test_apex_canonical_is_reported_and_unset_canonical_is_not(self):
        self.assertEqual(self.s["canonical_other_host"], [SITE + "/blog/x.html"])

    def test_different_url_on_same_host_is_reported_separately(self):
        self.assertEqual([x["url"] for x in self.s["canonical_other_url"]], [SITE + "/study/polity/index.html"])

    def test_home_trailing_slash_is_not_a_mismatch(self):
        self.assertNotIn(SITE + "/", [x["url"] for x in self.s["canonical_other_url"]])


if __name__ == "__main__":
    unittest.main()
