# AspirantDaily.com — SEO Audit

**Date:** 2026-10-20 · **Scope:** the whole repository (135 HTML pages, static site on Vercel), the live host, and the Search Console exports in `search console/` (Page-indexing drilldowns exported 2026-10-18).

## How this audit was done, and its limits

| Source | What it gave | Verified? |
|---|---|---|
| Repository crawl (`scripts/seo_check.py`, plus a one-off crawler) | Titles, descriptions, H1s, canonicals, robots meta, JSON-LD, internal links, sitemap membership for all 135 pages | Yes |
| Git history | When each page was added and when its visible text last changed substantively | Yes |
| Live HTTP checks (curl, 2026-10-20) | Status codes, redirects, headers; live `sitemap.xml` and `robots.txt` match the repo at `76044cd` | Yes |
| Search Console Page-indexing exports (5 issue drilldowns, sample URLs + 90-day chart) | Which URLs Google reported under each issue and when it last crawled them | Yes, but these are **samples** and most crawl dates predate the Oct 18 fix |
| Search Console **Performance** data (clicks, impressions, queries, positions) | Not available in the repo | **No.** No traffic, CTR or ranking figures appear in this audit |
| Web search | Checks on 2025 exam dates (UPSC, SSC CGL, IBPS PO) | Secondary sources (aggregators), cited below |

Anything not in the "verified" rows is labelled as a hypothesis.

## Executive summary

1. **Root cause of the indexing failure (confirmed, fixed on Oct 18, awaiting recrawl):** until commit `edf3c0b` (2026-10-18), every canonical tag, the sitemap and `robots.txt` pointed at `https://aspirantdaily.com/…`. That host **307-redirects** to `https://www.aspirantdaily.com/…`, and 24 current-affairs pages had no canonical at all. Google was told to index URLs that redirect elsewhere, and the pages they redirect to declared the redirecting URL as canonical. The exports show exactly that pattern: 42 apex URLs "Discovered – currently not indexed" (never crawled), 11 "Page with redirect", 13 www URLs "Alternate page with proper canonical tag", and 14 "Duplicate without user-selected canonical". The fix is deployed (the live sitemap and robots match the repo). Most of the export crawl dates (Sep 19–30) predate it.
2. **Resolved in the Vercel dashboard (not by a code change):** the apex→www redirect was **307 (temporary)** in the first check on 2026-10-20 and returned **308** on the re-check later the same day. It is a Vercel **Domains** setting. `vercel.json` only adds `/index.html` → `/`.
3. **Content trust problems that undermine "helpful content" signals (confirmed, fixed in this change):**
   - The Exam Calendar told users its dates were "Verified" and "All 2025 dates are confirmed", but they conflict with published sources. UPSC CSE 2025 was notified on Jan 22 (not Feb 12) and its Mains began Aug 22 (not Sep 20). IBPS PO 2025 Prelims were on Aug 17/23/24 (not Oct 18–19). The SSC CGL 2025 notification came on Jun 9 (not Apr 10).
   - A blog post listed "Appeared in: 2020, 2022, 2024"-style UPSC year attributions for 10 questions with no source. These read as fabricated previous-year-question claims. Six cheat-code pages promised "Guaranteed marks!".
   - Structured data invented an organisation ("Current Affairs Hub") with social profiles the site does not own, used an "Editorial Team" Person author, and carried an impossible 2024 publish date.
   - Freshness signals were inflated. 33 current-affairs pages showed "Last updated: Sep 2026" although git shows their text last changed in March 2026. All 131 sitemap `lastmod` values were the same timestamp.
4. **Open, high risk:** 59 of the 135 pages (51 study notes) were added on a single day (2026-10-18), on top of 33 templated current-affairs pages. That is a scaled-content risk pattern regardless of the quality of any single page. The response should be editorial review and differentiation (see `SEO_CONTENT_ROADMAP.md`), not more pages.
5. **Open, high:** 11 pages still target "2025" exam syllabi and patterns during the 2026–27 cycle. I did not bump the years, because each needs checking against the new official notification.

The technical base is otherwise sound. There are no broken internal links, no accidental noindex, no duplicate titles, and the HTTP 404s are real 404s. All study content is server-rendered HTML.

## Confirmed issues

Severity: **Critical** blocks indexing or misleads users on facts; **High** materially weakens quality or crawl signals; **Medium** is a meaningful clean-up; **Low** is minor.

| # | Sev. | Issue | Evidence | Affected | Root cause | Fix | Status |
|---|---|---|---|---|---|---|---|
| C1 | Critical | Canonical / sitemap host conflict | `git show edf3c0b^:index.html` → `canonical https://aspirantdaily.com/`; old sitemap and robots on apex; apex 307→www (curl). GSC: 42 discovered-not-indexed (all apex), 11 page-with-redirect, 13 alternate-with-canonical, 14 duplicate-without-canonical | All pages | Host chosen in Vercel (www) ≠ host declared in HTML/sitemap | Point everything at `https://www.aspirantdaily.com` | **Fixed 2026-10-18 (`edf3c0b`), deployed.** Awaiting recrawl |
| C2 | Critical | Apex→www redirect is temporary | `curl -I https://aspirantdaily.com/` → `307`; `http://` → `308` | Whole host | Vercel domain redirect left on 307 | Vercel → Project → Settings → Domains → `aspirantdaily.com` → Redirect to `www.aspirantdaily.com` with **308 Permanent** | **Resolved 2026-10-20** in Vercel Domains (live re-check: apex → 308). Not changed by code |
| C3 | Critical | Exam calendar dates wrong but labelled "verified/confirmed" | Compared with ClearIAS / Careers360 / Business Standard reports (sources below) | `exam-calendar.html` (linked from 44 pages) | Dates not taken from official notices | Rebuilt as an official-sources directory with a visible correction notice; unverifiable dates removed | **Fixed** |
| H1 | High | Unsourced PYQ year attributions and "guaranteed marks" claims | 10× "Appeared in: <years>" in one post; "Guaranteed marks!" in 6 meta descriptions; "repeated every year", "have appeared repeatedly … 2020 to 2025" | `blog/10-most-repeated-…`, `repeated-questions/*`, homepage, hubs | Marketing copy presented as fact | Year tags removed; reframed as "practice questions on high-frequency topics" with an explicit not-actual-PYQ note and a link to UPSC's official papers. Q8 answer corrected (special status = Art. 370; 35A came via a 1954 Presidential Order under 370) | **Fixed** (URLs kept) |
| H2 | High | Misleading structured data | `climate-summit-outcomes.html`: `EducationalOrganization` "Current Affairs Hub" + 3 foreign `sameAs` profiles. `indian-net-zero-target.html`: Person "Editorial Team", publisher "Current Affairs Hub", `datePublished 2024-01-15` (repo began 2025-12-14). 8 pages: inflated `wordCount` (e.g. claims 3700 vs ~2,370 visible) | 10 pages | Copied templates | Replaced with Article + BreadcrumbList by AspirantDaily using git dates; `wordCount` removed | **Fixed** |
| H3 | High | Inflated freshness signals | Sitemap: 131× identical `2026-10-18T18:00`. Visible "Last updated: Sep 2026" on 33 CA pages whose text last changed 2026-03-25/30. 16 `dateModified` values that disagree with git | Sitemap, 33 CA pages, 16 JSON-LD blocks | Dates bumped by hand to trigger recrawl | `scripts/build_sitemap.py` now derives `lastmod` from the last **substantive** text change in git. Visible dates and `dateModified` aligned to the same rule | **Fixed** |
| H4 | High | Scaled-content velocity | `git log --diff-filter=A`: 59 pages added 2026-10-18; 33 CA pages share one template | `study/**` | Bulk publishing | Editorial review per page; prioritise depth over count (roadmap) | **Open** |
| H5 | High | Stale "2025" exam targeting during the 2026–27 cycle | 11 titles contain 2025 (list in roadmap) | Syllabus/strategy posts, 2 cheat codes | Not refreshed | Re-verify each against the latest official notification, then update content, title and date together | **Partly fixed 2026-10-20**: UPSC Prelims, SSC CGL syllabus and SSC 180+ strategy rewritten against official notices (see "2026-10-20 update"). 3 titles are correct as-is. Bank, RRB and PSC syllabus posts are still open; the banking and economy cheat codes are dated December 2025 facts, with the repo rate updated |
| H6 | High | "Crawled – currently not indexed" on www URLs | GSC: `study/current-affairs/index.html`, `deepfake-regulation-in-india.html`, `aditya-l1-mission.html`, `repeated-questions/english-cheat-code.html` | 4 sample URLs | Hypothesis: quality/duplication signals (templated CA pages, thin cheat code), compounded by C1 | Improve per roadmap items 13–17 | **Open** |
| M1 | Medium | Visible keyword lists ("🔍 Quick Search: …") | 84 pages | Study + CA pages | SEO template | Removed | **Fixed** |
| M2 | Medium | CA pages missing OG / Article / Breadcrumb data; titles led with internal codes ("CA-03: …") | 23 pages with no OG or JSON-LD; 33 titles with `CA-NN` | `study/current-affairs/*` | Older template | OG + Article + BreadcrumbList added from visible content; codes dropped from titles; visible breadcrumb label "Home" → "Study Portal" (it links to the portal) | **Fixed** |
| M3 | Medium | Weak crawlable internal linking | Homepage subject cards are `href="#"` JS links to a noindex quiz; homepage linked the 9 study hubs only through `/study/`. Cheat codes and study notes did not link to each other | Homepage, 9 cheat codes, 8 hubs | UI built for the quiz | Added a "Study Notes by Subject" grid (9 links) to the homepage; cheat code ↔ study hub contextual links | **Fixed** |
| M4 | Medium | og:url / canonical mismatches | `repeated-questions/index.html` og:url and JSON-LD url = `/blog/`; `blog/index.html` og:url `/blog/` vs canonical `/blog/index.html`; `quiz.html`/`result.html` og:url = homepage | 4 pages | Copy-paste | Corrected; the checker now fails on any mismatch | **Fixed** |
| M5 | Medium | Contradictory directives on `result.html` | `noindex` + canonical → homepage | 1 page | — | Canonical removed (noindex kept) | **Fixed** |
| M6 | Medium | Duplicate homepage URL | GSC lists `www…/index.html` as alternate; 96 internal links used `/index.html` | Homepage | — | Internal links → `/`; `vercel.json` 308 `/index.html` → `/` | **Fixed** (redirect takes effect on deploy) |
| M7 | Medium | Inaccurate homepage claims | "100 Q" Quant (bank has 60), "50 Q" Reasoning (69), "25 fresh questions every day" (date-seeded reshuffle of a static pool), "verified, and updated monthly", PDF mislabelled "Exam Calendar 2025 Schedule (All Exams)" (it is UPSC's 2026 programme), "SSC GK 2025 – Latest Current Affairs" (it is static GK) | `index.html` | — | Rewritten to match reality | **Fixed** |
| M8 | Medium | Trust / ownership signals | No About or editorial-policy page; contact email is `support@teachings.ai`; kids-learning promo on exam pages | Site-wide | — | Owner to add an honest About/Editorial page with real ownership and correction policy (not fabricated credentials) | **Open (owner input needed)** |
| M9 | Medium | Core MCQ bank not indexable | ~538 bilingual questions in `data/*.json`, rendered client-side on `quiz.html` (noindex). Many are trivial ("capital of France") | Quiz | By design | Keep noindex. Do **not** mass-publish this bank as pages. Curate exam-level sets first (roadmap) | **Open (by design)** |
| L1 | Low | Long titles | 64 titles > 75 chars (mostly study notes listing every subtopic) | `study/**` | — | Shorten when each page is next edited | Open |
| L2 | Low | Section index URL variants | `/study/polity`, `/study/polity/` and `/study/polity/index.html` all return 200 | 10 hubs | Vercel static defaults | Self-canonical to `…/index.html` already consolidates; optional future move to directory URLs + 308s | Open (low risk) |
| L3 | Low | ~10 KB inline CSS duplicated per study page | Median page 10 KB; CA pages up to 61 KB | `study/**` | Per-page templates | Move to `study/styles.css` when templates are next touched | Open |
| L4 | Low | FAQPage markup on 90+ pages | Google shows FAQ rich results only for authoritative government/health sites (since 2023) | Study notes | — | Harmless; FAQ text is visible on page. No action | Accepted |
| L5 | Low | "free marks" promotional phrasing | 9 occurrences | Cheat codes, 2 blog posts | — | Tone down on next edit | Open |
| L6 | Low | Out-of-date topical content | `g20-summit.html` covers only the 2023 Indian presidency | CA pages | — | Roadmap item 10 | Open |

### Verified as correct (no change needed)

- `robots.txt` allows everything except `/admin.html` and lists the www sitemap. `admin.html`, `quiz.html`, `quiz-selector.html` and `result.html` are deliberately `noindex`.
- 0 broken internal links across 135 pages. 0 duplicate titles. Every indexable page has a meta description and exactly one H1.
- Unknown URLs return a real **404** (no soft-404 risk from a catch-all). HTTPS with HSTS. `http://` → `https://` is 308.
- All educational content is in the initial HTML. Collapsible sections hide content with CSS only, so no JavaScript rendering dependency for notes.
- `lang="en"` and the viewport meta tag are present everywhere. No images in content, so no lazy-loading or CLS issues from media. GA and AdSense load `async`.
- At 375 px width, the 10 changed templates measured `scrollWidth = 360` (the iframe minus its scrollbar), so there is no horizontal page scroll.

## Search Console exports: interpretation

Run `python scripts/gsc_report.py "search console"` to regenerate this classification.

| Issue (sample size) | Classification against the current site | Reading |
|---|---|---|
| Discovered – currently not indexed (42) | 42/42 are apex `aspirantdaily.com` URLs, "last crawled 1970-01-01" (never) | Effect of C1. These should drop out as Google follows www canonicals. They need the C2 fix to resolve cleanly |
| Page with redirect (11) | 11/11 apex or `http://` URLs | Expected and correct once the www host is canonical |
| Alternate page with proper canonical tag (13) | 10 are www URLs that are now self-canonical; 2 are `quiz.html?exam=` URLs; 1 is `/index.html` | The 10 were crawled Sep 20–30, when their canonical still pointed at apex (C1). Query URLs and `/index.html` are correctly alternates |
| Duplicate without user-selected canonical (14) | 14/14 www URLs now self-canonical and in the sitemap | All 14 lacked a canonical before `edf3c0b` (or were section hubs reachable at several URLs). Should resolve on recrawl |
| Crawled – currently not indexed (4) | 4/4 www, canonical, in sitemap | The only bucket not explained by C1. Treat as a quality signal (H6) |

The issue chart shows these buckets jumping on **2026-09-19**, the day 6 pages were added and the site was evidently re-submitted.

## Validation procedure

1. `python scripts/seo_check.py` must exit 0 (it currently does: 135 pages, 131 indexable, 131 in sitemap, 0 errors).
2. After deploying, run `curl -sI https://www.aspirantdaily.com/index.html`. It should return 308 to `/`. After C2, `curl -sI https://aspirantdaily.com/` should return **308**.
3. Search Console → Sitemaps: resubmit `https://www.aspirantdaily.com/sitemap.xml`. URL Inspection → "Test live URL" on the homepage, one study note, one CA page and the exam calendar. Check "User-declared canonical" = "Google-selected canonical" = the www URL.
4. Over 2–6 weeks, Page indexing should show the apex buckets shrinking and "Indexed" rising. A sitemap submission is **not** proof of indexing. Only the Indexed count and URL Inspection are. See `SEO_MONITORING.md`.

## Sources used for the exam-date check

- UPSC CSE 2025 notification (Jan 22, 2025), Prelims May 25, Mains from Aug 22: [ClearIAS](https://www.clearias.com/upsc-cse-2025-notification/), [Careers360](https://news.careers360.com/upsc-cse-exam-2025-date-prelims-may-25-notification-out-application-form-begins-upsconline-gov-in-calendar/amp)
- SSC CGL 2025 notification (Jun 9, 2025), Tier 1 originally Aug 13–30 and later rescheduled: [Business Standard](https://www.business-standard.com/education/news/ssc-cgl-2025-exam-dates-and-city-information-released-on-official-website-nc-125080600552_1.html), [PW](https://store.pw.live/blogs/ssc-exams/ssc-cgl-2025-notification-out)
- IBPS PO 2025 notification (Jun 30/Jul 1), Prelims Aug 17/23/24, Mains Oct 12: [Careers360](https://competition.careers360.com/articles/ibps-po-2025), [PW](https://www.pw.live/banking/exams/ibps-po-exam-date-2025)

These are secondary sources. That is why the rebuilt calendar page lists only official sources and no dates of its own.

## 2026-10-20 update

### Titles and content checked against official notices

| Page (URL unchanged) | New title | Official source checked |
|---|---|---|
| `blog/upsc-prelims-syllabus-2025.html` | UPSC Prelims Syllabus & Exam Pattern (CSE 2026 Notice) | [UPSC Examination Notice No. 05/2026-CSE, 04.02.2026](https://www.upsc.gov.in/sites/default/files/Notif-CSP-2026-Engl-060226Rev.pdf), Appendix I. Removed the claims that there is no negative marking for decision-making questions and the unsourced question counts |
| `blog/ssc-cgl-syllabus-2025.html` | SSC CGL 2026 Syllabus & Exam Pattern (Official Notice) | [SSC CGL 2026 notice](https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_cgl_2025.pdf) (paras 13.8–13.11, 16); [Tier-I schedule notice, 12.09.2026](https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Important%20Notice%202026_cgle_2026_12092026.pdf) |
| `blog/how-to-score-180-ssc-cgl-tier1.html` | SSC CGL Tier 1: How to Score 180+ (2026 Pattern) | Same CGL 2026 notice. Removed the "2-pass, 40 + 20 minutes" and "GA first in 8–10 minutes" advice, which is impossible under the new 15-minute sectional timers. Also removed "used by toppers" and the unsourced per-topic question counts |

Left as-is, with correct years: `blog/current-affairs-dec-2025-summary.html` and `blog/top-25-current-affairs-mcqs-december-2025.html` are month archives. `study/economy/taxation-and-gst.html` uses "Income-tax Act, 2025", the statute's name.

Not yet verified (titles unchanged, no dates invented):

| Page | Sources needed |
|---|---|
| `blog/bank-exam-syllabus-2025.html` | IBPS PO/Clerk CRP notices ([ibps.in](https://www.ibps.in/), unreachable from this environment); SBI PO/Clerk ([sbi.bank.in/web/careers](https://sbi.bank.in/web/careers)); RBI Grade B ([opportunities.rbi.org.in](https://opportunities.rbi.org.in/)) |
| `blog/rrb-syllabus-2025.html` | Current RRB CEN notices for NTPC, Group D and JE ([rrbapply.gov.in](https://rrbapply.gov.in/), unreachable from this environment; also each RRB's regional site) |
| `blog/psc-syllabus-2025.html` | [uppsc.up.nic.in](https://uppsc.up.nic.in/), [mppsc.mp.gov.in](https://mppsc.mp.gov.in/), [tnpsc.gov.in](https://www.tnpsc.gov.in/), [bpsc.bihar.gov.in](https://bpsc.bihar.gov.in/) |

### Claims removed (extends H1)

- Removed "guarantee N+ marks", "N questions repeat yearly" and "All facts/data verified from … papers (2020–2025)" from 8 cheat codes, 2 blog posts and the blog index. None of these claims had a source. Each note now reads "Compiled by AspirantDaily … not an official answer key".
- `og:description` on 8 cheat codes: "to score N+ marks" → "most often asked in".

### Factual corrections from the spot check of the October 18 notes

- Repo rate. [rbi.org.in](https://www.rbi.org.in/) (page updated 19 Oct 2026) shows Repo 5.50%, SDF 5.25%, MSF and Bank Rate 5.75%, CRR 3.00% and SLR 18.00%. The [RBI monetary policy page](https://www.rbi.org.in/Scripts/Annualpolicy.aspx) lists the policy of Oct 7, 2026 (MPC Oct 5–7), and the pages still showed the December 2025 values. Updated `study/economy/money-banking-and-rbi.html`, `repeated-questions/banking-awareness-cheat-code.html`, `repeated-questions/economy-cheat-code.html` and `blog/top-15-banking-terms-ibps-sbi-exams.html`. The December 2025 month archives keep the December values, which were correct at the time.
- Spot-checked; no change needed: ISFR 2023 headline figures (25.17% / 21.76% / 3.41%, 8,27,357 sq km). 58 tiger reserves, Madhav the latest (Mar 2025); no 59th found. Ramsar "more than 90" is still true (secondary sources report 98 or more in 2026). GII 2025 rank 38. VB-G RAM G Act in force from 1 July 2026 (secondary reports of the Ministry of Rural Development notification, not the Gazette text).
- **This is a spot check, not a fact-check.** None of the 51 study notes has been reviewed line by line against primary sources. Do not label any of them "fact-checked" or "verified".
