"""Shared helpers for the SEO scripts: page discovery, parsing and git dates."""
import os
import subprocess
from datetime import date
from difflib import SequenceMatcher
from functools import lru_cache

from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "https://www.aspirantdaily.com"
SKIP_DIRS = {".git", ".vscode", "node_modules", "scripts", "search console", "content", "tests"}


def html_pages():
    """Yield site-relative paths (forward slashes) of every HTML page."""
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name.endswith(".html"):
                full = os.path.join(dirpath, name)
                yield os.path.relpath(full, ROOT).replace(os.sep, "/")


def url_for(rel):
    """Canonical URL for a page path. The homepage is served at the root."""
    return HOST + "/" if rel == "index.html" else HOST + "/" + rel


def soup_for(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return BeautifulSoup(fh.read(), "lxml")


def robots_of(soup):
    tag = soup.find("meta", attrs={"name": "robots"})
    return (tag.get("content") or "").lower() if tag else ""


def canonical_of(soup):
    tags = soup.find_all("link", rel="canonical")
    return [t.get("href") for t in tags]


def is_indexable(rel, soup):
    return "noindex" not in robots_of(soup) and canonical_of(soup) == [url_for(rel)]


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8").stdout


def _words(html):
    """Visible words of the page's main content (no nav, header, footer)."""
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    body = soup.body
    if body is None:
        return []
    for tag in body.find_all(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    return body.get_text(" ").split()


def _substantive(old, new):
    """True when the visible text changed by more than ~2% or 40 words."""
    if not old:
        return True
    changed = sum(n for tag, *_, n in _diff_ops(old, new) if tag != "equal")
    return changed > max(40, 0.02 * len(new))


def _diff_ops(old, new):
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        yield tag, max(i2 - i1, j2 - j1)


@lru_cache(maxsize=None)
def git_dates(rel):
    """(first_published, last_substantive_change) as ISO dates from git history.

    A commit counts as a content change only when it substantively altered the
    visible main text, so metadata, navigation and layout edits do not bump the
    date. Uncommitted substantive edits count as today. Returns (None, None)
    for files git does not know about.
    """
    log = _git("log", "--follow", "--format=%H %as", "--", rel).split("\n")
    commits = [line.split() for line in log if line.strip()]
    if not commits:
        return None, None
    first = commits[-1][1]
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        current = _words(fh.read())
    if _substantive(_words(_git("show", f"HEAD:{rel}")), current):
        return first, date.today().isoformat()
    for i, (sha, day) in enumerate(commits):
        older = commits[i + 1][0] if i + 1 < len(commits) else None
        new = _words(_git("show", f"{sha}:{rel}"))
        old = _words(_git("show", f"{older}:{rel}")) if older else []
        if _substantive(old, new):
            return first, day
    return first, first
