# AspirantDaily.com — SEO Monitoring Workflow

**Date:** 2026-10-20

There is no Search Console API access configured for this repository. The workflow below therefore runs on **manual CSV exports** from Search Console plus the local scripts in `scripts/`. If API access is added later, the same report script can be fed with API output saved as CSV.

## Tools in this repo

| Command | What it does | When |
|---|---|---|
| `python scripts/seo_check.py` | Static checks over all pages: broken internal links, canonical/og:url consistency, titles/descriptions/H1, valid JSON-LD with no future dates, sitemap ↔ indexable-page agreement, robots.txt sitemap line. Exits 1 on any error | Before every commit/deploy |
| `python scripts/build_sitemap.py` | Rewrites `sitemap.xml` with only indexable, self-canonical pages. `lastmod` = date of the last **substantive** change to visible text in git (or today, for uncommitted substantive edits) | After adding/removing pages or editing content, then rerun the check |
| `python scripts/gsc_report.py "<exports folder>"` | Classifies every URL in Page-indexing drilldown exports against the current site (canonical/in sitemap/404/non-canonical host) | Weekly, after exporting |
| `python scripts/gsc_report.py --pages cur/Pages.csv --prev-pages prev/Pages.csv --queries cur/Queries.csv --prev-queries prev/Queries.csv` | Performance summary: near-page-one URLs (pos 8–20), low-CTR rows, biggest gainers/losers between two periods | Monthly |

Requirements: Python 3.10+ with `beautifulsoup4` and `lxml` (`pip install beautifulsoup4 lxml`), and `git` on PATH (for dates).

## Data to export from Search Console (property: `https://www.aspirantdaily.com/` or the domain property)

1. **Page indexing:** Indexing → Pages. For each issue row ("Discovered – currently not indexed", "Crawled – currently not indexed", "Duplicate without user-selected canonical", "Alternate page with proper canonical tag", "Page with redirect", "Not found (404)"), open it and use **Export → Download CSV**. Unzip each into `search console/<date>/<issue>/` (each must contain `Metadata.csv` and `Table.csv`). Also record the headline **Indexed** and **Not indexed** totals by hand in the log below. The drilldown CSVs are samples, not totals.
2. **Performance:** Performance → Search results → Date range "Last 3 months" → Export. Then set **Compare → Last 3 months vs previous period** and export again. Keep `Pages.csv` and `Queries.csv` from each.
3. **Sitemaps:** Indexing → Sitemaps. Note "Discovered pages" for `https://www.aspirantdaily.com/sitemap.xml`.

Keep the raw exports out of git, or in a dated folder if you want history. The current `search console/` folder is untracked.

## Schedule

| Cadence | Task |
|---|---|
| Every deploy | `seo_check.py` must pass. If pages or content changed, run `build_sitemap.py` first |
| Weekly (first 8 weeks after the 2026-10-18/20 fixes) | Export Page indexing → `gsc_report.py`. Record Indexed / Not indexed totals. URL-inspect 3 sample pages (one study note, one CA note, one blog post) and confirm Google-selected canonical = the www URL |
| Monthly | Performance export and compare → `gsc_report.py --pages … --prev-pages …`. Update the roadmap priority order using near-page-one and low-CTR lists |
| Quarterly | Re-run the full audit checklist in `SEO_AUDIT.md`; re-verify exam dates and syllabus pages against official notices |

## What to track (log table)

Append one row per weekly check. Fill in only numbers read from Search Console; leave blanks rather than estimating.

| Date | Indexed | Not indexed | Discovered-not-indexed | Crawled-not-indexed | Duplicate w/o canonical | Alternate w/ canonical | Page w/ redirect | Clicks (28d) | Impressions (28d) | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-18 (exports) | — | — | 42 (sample) | 4 (sample) | 14 (sample) | 13 (sample) | 11 (sample) | — | — | Baseline from drilldown samples; totals not exported |

Also keep a short changelog of content updates (page, date, what changed). That lets movements in Performance be attributed to specific edits.

## How to read the results

- **Expected after the www-canonical fix (C1) and the 308 fix (C2):** apex URLs move into "Page with redirect" and stop appearing elsewhere. "Duplicate without user-selected canonical" and "Alternate page with proper canonical tag" stop listing www pages that are self-canonical. "Indexed" rises. Allow 2–6 weeks; small sites are recrawled slowly.
- **A sitemap submission or "Discovered pages" count is not indexing.** Only the Indexed count and URL Inspection ("URL is on Google") count as success.
- **"Crawled – currently not indexed"** that persists after the canonical fixes is a quality signal. Improve the page (roadmap) rather than resubmitting it.
- **Do not** bump dates, `lastmod` or "Last updated" labels to provoke recrawls. The sitemap builder deliberately ignores non-substantive edits.

## Owner actions that only the site owner can do

1. Vercel → Project → Settings → Domains: `aspirantdaily.com` must redirect to `www.aspirantdaily.com` with **308 Permanent**. The re-check on 2026-10-20 already returned 308; keep it that way. Verify with `curl -sI https://aspirantdaily.com/`.
2. After approving the commit, deploy it. Check that `curl -sI https://www.aspirantdaily.com/index.html` returns 308 to `/` (from `vercel.json`). Then resubmit the sitemap in Search Console and request indexing for the homepage, `/study/index.html`, `/exam-calendar.html` and the three rewritten exam pages (UPSC Prelims syllabus, SSC CGL syllabus, SSC 180+).
3. Confirm the Search Console property in use covers `https://www.aspirantdaily.com/` (a Domain property covers both hosts).
