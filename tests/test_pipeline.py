"""Tests for the content pipeline: validators, selection, review gating and safe publishing.

Run: python -X utf8 -m unittest discover -s tests -v
"""
import contextlib
import csv
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import content_lib  # noqa: E402
import content_pipeline  # noqa: E402
from content_validate import safe_eval, validate_draft  # noqa: E402

GOOD_ID = "successive-discount-formula"
# A copy of the batch-001 draft, so the tests do not depend on the working drafts.
GOOD = os.path.join(ROOT, "tests", "fixtures", GOOD_ID + ".html")


def topics():
    return {t["id"]: t for t in content_lib.read_topics()}


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            code = content_pipeline.main(list(argv))
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue()


class ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(GOOD, encoding="utf-8") as fh:
            cls.good = fh.read()
        cls.row = topics()[GOOD_ID]

    def errors(self, text):
        planned = {"__planned__": {t["path"] for t in topics().values()}}
        return validate_draft(text, self.row, other_drafts=planned)[0]

    def test_good_draft_passes(self):
        self.assertEqual(self.errors(self.good), [])

    def test_wrong_computation_is_rejected(self):
        bad = self.good.replace('"expect": 28}', '"expect": 30}')
        self.assertTrue(any("check c1" in e for e in self.errors(bad)))

    def test_wrong_answer_key_is_rejected(self):
        bad = self.good.replace('"answer": 1, "explanation": "Using a + b', '"answer": 0, "explanation": "Using a + b')
        self.assertTrue(any("does not match check" in e for e in self.errors(bad)))

    def test_guarantee_claim_is_rejected(self):
        bad = self.good.replace("<p>A successive discount", "<p>We guarantee selection. A successive discount")
        self.assertTrue(any("guarantee" in e for e in self.errors(bad)))

    def test_constitutional_use_of_guarantee_is_allowed(self):
        ok = self.good.replace("<p>A successive discount", "<p>Article 32 guarantees the right to move the Court. A successive discount")
        self.assertFalse(any("guarantee" in e for e in self.errors(ok)))

    def test_self_declared_fact_check_is_rejected(self):
        bad = self.good.replace("<p>A successive discount", "<p>This page is fact-checked. A successive discount")
        self.assertTrue(any("review status" in e for e in self.errors(bad)))

    def test_unsourced_pyq_claim_is_rejected(self):
        bad = self.good.replace("<p>A successive discount", "<p>This was asked in SSC CGL 2023. A successive discount")
        self.assertTrue(any("previous-year" in e for e in self.errors(bad)))

    def test_thin_content_is_rejected(self):
        meta = re.search(r'<script type="application/json" id="draft-meta">.*?</script>', self.good, re.S).group(0)
        thin = meta + '\n<section data-heading="A"><p>Short.</p></section><section data-heading="B"><p>x</p></section>' \
                      '<section data-heading="C"><p>y</p></section>'
        self.assertTrue(any("thin content" in e for e in self.errors(thin)))

    def test_repeated_paragraph_is_rejected(self):
        para = "<p>" + " ".join(["repeated"] * 5 + ["words", "make", "a", "paragraph", "long", "enough", "to", "count"]) + "</p>"
        bad = self.good.replace("</section>", para + para + "</section>", 1)
        self.assertTrue(any("repeated paragraph" in e for e in self.errors(bad)))

    def test_claim_with_unknown_source_is_rejected(self):
        bad = self.good.replace('"claims": []', '"claims": [{"text": "x", "source": "nope", "locator": "", "agent_check": "matched"}]')
        self.assertTrue(any("unknown source" in e for e in self.errors(bad)))

    def test_broken_internal_link_is_rejected(self):
        bad = self.good.replace('href="../../repeated-questions/quant-cheat-code.html"', 'href="../../no-such-page.html"', 1)
        self.assertTrue(any("broken internal link" in e for e in self.errors(bad)))

    def test_safe_eval_refuses_code(self):
        for expr in ("__import__('os')", "open('x')", "(1).real", "[x for x in (1,)]"):
            with self.assertRaises(ValueError):
                safe_eval(expr)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.saved = (content_lib.STATE_PATH, content_lib.DRAFTS_DIR, content_lib.CONTENT, content_pipeline.ROOT)
        content_lib.CONTENT = os.path.join(self.tmp, "content")
        content_lib.STATE_PATH = os.path.join(self.tmp, "content", "state.json")
        content_lib.DRAFTS_DIR = os.path.join(self.tmp, "content", "drafts")
        content_pipeline.ROOT = self.tmp
        os.makedirs(content_lib.DRAFTS_DIR)
        with open(GOOD, encoding="utf-8") as fh:
            text = fh.read()
        # The fixture links to a sibling draft; point it at an existing page so it can publish alone.
        text = text.replace('href="product-constancy-price-and-consumption.html"',
                            'href="../../repeated-questions/quant-cheat-code.html"')
        with open(os.path.join(content_lib.DRAFTS_DIR, GOOD_ID + ".html"), "w", encoding="utf-8") as fh:
            fh.write(text)
        # Stubs for the shared files every rendered page links to.
        for rel in ("index.html", "contact.html", "favicon.svg", "study/index.html", "styles.css",
                    "study/scripts.js", "repeated-questions/quant-cheat-code.html"):
            os.makedirs(os.path.dirname(os.path.join(self.tmp, rel)), exist_ok=True)
            with open(os.path.join(self.tmp, rel), "w", encoding="utf-8") as fh:
                fh.write('<html><main><a href="study/index.html">Study</a></main></html>' if rel == "index.html"
                         else "<html><main></main></html>")

    def tearDown(self):
        content_lib.STATE_PATH, content_lib.DRAFTS_DIR, content_lib.CONTENT, content_pipeline.ROOT = self.saved
        shutil.rmtree(self.tmp)

    def state(self):
        with open(content_lib.STATE_PATH, encoding="utf-8") as fh:
            return json.load(fh)

    def test_select_is_idempotent_and_never_duplicates(self):
        run("select", "--batch-size", "5")
        run("select", "--batch-size", "5")
        batches = self.state()["batches"]
        ids = [i for b in batches.values() for i in b["ids"]]
        self.assertEqual(len(ids), 10)
        self.assertEqual(len(ids), len(set(ids)))
        code, out = run("select", "--ids", ",".join(batches["batch-001"]["ids"]))
        self.assertIn("already holds", out)
        self.assertEqual(len(self.state()["batches"]), 2)

    def test_scaffold_never_overwrites(self):
        run("select", "--ids", GOOD_ID)
        before = open(os.path.join(content_lib.DRAFTS_DIR, GOOD_ID + ".html"), encoding="utf-8").read()
        run("scaffold", "--batch", "batch-001")
        after = open(os.path.join(content_lib.DRAFTS_DIR, GOOD_ID + ".html"), encoding="utf-8").read()
        self.assertEqual(before, after)

    def test_publish_requires_approval_and_protects_manual_edits(self):
        run("select", "--ids", GOOD_ID)
        run("validate", "--batch", "batch-001")
        self.assertEqual(self.state()["pages"][GOOD_ID]["status"], "drafted")
        page = os.path.join(self.tmp, "study", "quant", GOOD_ID + ".html")

        code, out = run("publish", "--batch", "batch-001", "--no-site-checks")
        self.assertIn("only approved pages are published", out)
        self.assertFalse(os.path.exists(page))

        code, out = run("review", "--id", GOOD_ID, "--status", "approved", "--reviewer", "Test Reviewer")
        self.assertNotEqual(code, 0)  # approval without a fact-check is refused
        run("review", "--id", GOOD_ID, "--status", "approved", "--reviewer", "Test Reviewer", "--with-fact-check")
        self.assertEqual(self.state()["pages"][GOOD_ID]["status"], "approved")

        code, out = run("publish", "--batch", "batch-001", "--no-site-checks")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.exists(page))
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "study", "quant", "index.html")))
        html = open(page, encoding="utf-8").read()
        self.assertIn("Reviewed by Test Reviewer", html)
        self.assertIn('content="index, follow"', html)

        code, out = run("publish", "--batch", "batch-001", "--no-site-checks")
        self.assertIn("same", out)

        with open(page, "a", encoding="utf-8") as fh:
            fh.write("<!-- manual edit -->")
        code, out = run("publish", "--batch", "batch-001", "--no-site-checks")
        self.assertNotEqual(code, 0)
        self.assertIn("REFUSED", out)
        self.assertTrue(open(page, encoding="utf-8").read().endswith("<!-- manual edit -->"))

    def test_series_links_neighbours_and_keeps_republish_quiet(self):
        run("select", "--ids", GOOD_ID)
        run("validate", "--batch", "batch-001")
        run("review", "--id", GOOD_ID, "--status", "approved", "--reviewer", "Test Reviewer", "--with-fact-check")
        self.assertEqual(run("publish", "--batch", "batch-001", "--no-site-checks")[0], 0)
        page = os.path.join(self.tmp, "study", "quant", GOOD_ID + ".html")
        state, topics = content_lib.load_state(), content_pipeline.topics_by_id()
        with open(os.path.join(self.tmp, "study", "quant", "other.html"), "w", encoding="utf-8") as fh:
            fh.write("<html><h1>Other Page</h1></html>")
        nav = content_pipeline.series_nav(topics[GOOD_ID]["path"], None, "study/quant/other.html")
        self.assertIn('href="other.html" class="nav-btn">Other Page →', nav)
        # A one-page series keeps the hub-only bar, and republishing finds nothing to change.
        self.assertEqual(content_pipeline.apply_series(state, topics, False), [])
        self.assertIn("same", run("publish", "--batch", "batch-001", "--no-site-checks")[1])
        # A bar edited by hand is left alone.
        text = open(page, encoding="utf-8").read()
        with open(page, "w", encoding="utf-8") as fh:
            fh.write(text.replace('<div class="page-navigation">', '<div class="page-navigation"><button>x</button>', 1))
        self.assertIn("REFUSED", content_pipeline.apply_series(state, topics, True)[0])

    def test_republish_accepts_page_from_crlf_draft(self):
        path = os.path.join(content_lib.DRAFTS_DIR, GOOD_ID + ".html")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text.replace("\n", "\r\n"))
        run("select", "--ids", GOOD_ID)
        run("validate", "--batch", "batch-001")
        run("review", "--id", GOOD_ID, "--status", "approved", "--reviewer", "Test Reviewer", "--with-fact-check")
        code, out = run("publish", "--batch", "batch-001", "--no-site-checks")
        self.assertEqual(code, 0, out)
        code, out = run("publish", "--batch", "batch-001", "--no-site-checks")
        self.assertEqual(code, 0, out)
        self.assertNotIn("REFUSED", out)

    def test_publish_holds_pages_linking_to_unpublished_pages(self):
        shutil.copy(GOOD, content_lib.DRAFTS_DIR)  # original draft links to an unpublished sibling
        run("select", "--ids", GOOD_ID)
        run("validate", "--batch", "batch-001")
        run("review", "--id", GOOD_ID, "--status", "approved", "--reviewer", "Test Reviewer", "--with-fact-check")
        code, out = run("publish", "--batch", "batch-001", "--no-site-checks")
        self.assertIn("links to pages that are not published", out)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "study", "quant", GOOD_ID + ".html")))

    def test_editing_after_review_resets_status(self):
        run("select", "--ids", GOOD_ID)
        run("validate", "--batch", "batch-001")
        run("review", "--id", GOOD_ID, "--status", "fact-checked", "--reviewer", "Test Reviewer")
        self.assertEqual(self.state()["pages"][GOOD_ID]["status"], "fact-checked")
        path = os.path.join(content_lib.DRAFTS_DIR, GOOD_ID + ".html")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace("A successive discount is", "A successive discount is simply"))
        run("validate", "--batch", "batch-001")
        self.assertEqual(self.state()["pages"][GOOD_ID]["status"], "drafted")

    def test_publish_is_all_or_nothing(self):
        run("select", "--ids", GOOD_ID)
        run("validate", "--batch", "batch-001")
        run("review", "--id", GOOD_ID, "--status", "approved", "--reviewer", "Test Reviewer", "--with-fact-check")
        # study/index.html carries a pipeline block someone edited by hand: the hub could not be linked.
        with open(os.path.join(self.tmp, "study", "index.html"), "w", encoding="utf-8") as fh:
            fh.write("<html><main>" + content_pipeline.BLOCK_START + "edited" + content_pipeline.BLOCK_END + "</main></html>")
        code, out = run("publish", "--batch", "batch-001", "--no-site-checks")
        self.assertNotEqual(code, 0)
        self.assertIn("nothing was written", out)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "study", "quant", GOOD_ID + ".html")))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "study", "quant", "index.html")))
        self.assertEqual(self.state()["pages"][GOOD_ID]["status"], "approved")

    def test_dry_run_writes_nothing(self):
        run("select", "--ids", GOOD_ID)
        run("validate", "--batch", "batch-001")
        run("review", "--id", GOOD_ID, "--status", "approved", "--reviewer", "Test Reviewer", "--with-fact-check")
        code, out = run("publish", "--batch", "batch-001", "--dry-run", "--no-site-checks")
        self.assertEqual(code, 0, out)
        self.assertIn("release checks passed", out)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "study", "quant", "index.html")))
        self.assertEqual(self.state()["pages"][GOOD_ID]["status"], "approved")

    def test_release_check_finds_orphans_and_broken_links(self):
        pending = {"study/quant/a.html": ('<a href="missing.html">x</a>', "file")}
        problems = content_pipeline.release_problems(pending, {"study/quant/a.html"})
        self.assertTrue(any("broken internal link to study/quant/missing.html" in p for p in problems))
        self.assertTrue(any("orphan" in p for p in problems))
        pending["study/quant/index.html"] = ('<a href="a.html">a</a><a href="../index.html">up</a>', "file")
        pending["study/quant/a.html"] = ('<a href="index.html">hub</a>', "file")
        # The hub and page link to each other, but nothing on the site links to the hub.
        problems = content_pipeline.release_problems(pending, {"study/quant/a.html", "study/quant/index.html"})
        self.assertEqual(problems, ["study/quant/a.html: orphan (not reachable by links from the home page)",
                                    "study/quant/index.html: orphan (not reachable by links from the home page)"])
        with open(os.path.join(self.tmp, "index.html"), "w", encoding="utf-8") as fh:
            fh.write('<a href="study/index.html">Study</a>')
        pending["study/index.html"] = ('<a href="quant/index.html">Quant</a>', "block")
        self.assertEqual(content_pipeline.release_problems(pending, {"study/quant/a.html", "study/quant/index.html"}), [])

    def test_render_previews_missing_hubs_as_noindex(self):
        run("select", "--ids", GOOD_ID)
        run("validate", "--batch", "batch-001")
        saved = content_pipeline.PREVIEW_DIR
        content_pipeline.PREVIEW_DIR = os.path.join(self.tmp, "content", "preview")
        try:
            run("render", "--batch", "batch-001")
        finally:
            content_pipeline.PREVIEW_DIR = saved
        hub = os.path.join(self.tmp, "content", "preview", "study", "quant", "index.html")
        self.assertIn('content="noindex, nofollow"', open(hub, encoding="utf-8").read())
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "study", "quant", "index.html")))

    def test_fact_check_needs_a_confirmed_decision_on_every_claim(self):
        path = os.path.join(content_lib.DRAFTS_DIR, GOOD_ID + ".html")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        source = ('{"id": "s1", "title": "T", "publisher": "P", "url": "https://www.legislative.gov.in/x.pdf", '
                  '"accessed": "2026-10-20", "supports": "S"}')
        claim = ('{"text": "Claim one.", "source": "s1", "locator": "Art. 1", "agent_check": "matched", '
                 '"passage": "exact words"}')
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace('"sources": []', f'"sources": [{source}]').replace('"claims": []', f'"claims": [{claim}]'))
        run("select", "--ids", GOOD_ID)
        run("validate", "--batch", "batch-001")
        run("claims", "--batch", "batch-001")
        sheet = content_pipeline.claims_csv("batch-001")

        def decide(decision, name):
            with open(sheet, encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.DictReader(fh))
            rows[0].update(reviewer_decision=decision, reviewer_name=name)
            with open(sheet, "w", encoding="utf-8-sig", newline="") as fh:
                w = csv.DictWriter(fh, content_pipeline.CLAIM_FIELDS)
                w.writeheader()
                w.writerows(rows)

        def fact_check():
            return run("review", "--id", GOOD_ID, "--status", "fact-checked", "--reviewer", "Test Reviewer")[0]

        self.assertNotEqual(fact_check(), 0)  # no decision yet
        decide("rejected", "Test Reviewer")
        self.assertNotEqual(fact_check(), 0)
        decide("confirmed", "")
        self.assertNotEqual(fact_check(), 0)  # decision without a name
        decide("confirmed", "Test Reviewer")
        self.assertEqual(fact_check(), 0)
        self.assertEqual(self.state()["pages"][GOOD_ID]["status"], "fact-checked")

        # Changing the claim resets the page and clears the stale decision.
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace("Claim one.", "Claim one, reworded."))
        run("validate", "--batch", "batch-001")
        self.assertEqual(self.state()["pages"][GOOD_ID]["status"], "drafted")
        code, out = run("claims", "--batch", "batch-001")
        self.assertIn("1 cleared", out)
        self.assertNotEqual(fact_check(), 0)

    def test_link_block_is_idempotent_and_guarded(self):
        rel = "parent.html"
        with open(os.path.join(self.tmp, rel), "w", encoding="utf-8", newline="") as fh:
            fh.write("<html>\r\n<main>\r\n<div class=\"page-navigation\"></div>\r\n</main>\r\n</html>\r\n")
        state = {"pages": {}, "batches": {}}
        block = content_pipeline.links_block(rel, [("study/quant/x.html", "X")], "Go deeper")
        self.assertIn("updated", content_pipeline.update_block(state, rel, block, False))
        self.assertIn("same", content_pipeline.update_block(state, rel, block, False))
        text = open(os.path.join(self.tmp, rel), encoding="utf-8", newline="").read()
        self.assertNotIn("\n", text.replace("\r\n", ""))  # CRLF preserved
        with open(os.path.join(self.tmp, rel), "w", encoding="utf-8", newline="") as fh:
            fh.write(text.replace(">X<", ">Edited by hand<"))
        block2 = content_pipeline.links_block(rel, [("study/quant/y.html", "Y")], "Go deeper")
        self.assertIn("REFUSED", content_pipeline.update_block(state, rel, block2, False))


if __name__ == "__main__":
    unittest.main()
