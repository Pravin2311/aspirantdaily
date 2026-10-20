# AspirantDaily.com — Content Roadmap

**Date:** 2026-10-20 · Companion to `SEO_AUDIT.md`.

## Evidence base, and what is missing

- **No Search Console Performance data** (queries, clicks, impressions, positions) was available. Priorities below therefore rest on three things: verified content state (accuracy, staleness, overlap, depth), the indexing evidence in the coverage exports, and the exam calendar (which cycles are coming up). **No search volumes or competition levels are claimed.**
- Once a Performance export exists, re-rank this list with `scripts/gsc_report.py` (see `SEO_MONITORING.md`). Pages with impressions at positions 8–20 and low CTR should jump the queue.
- Strategy: **improve and differentiate before adding.** 59 pages were published in one day (Oct 18). The next 6–8 weeks should go mostly into review and depth, with only a few new pages.

## Content inventory: classification

| Group | URLs | Class | Reason |
|---|---|---|---|
| Study notes: Polity, Economy, History, Geography, Environment, Science & Tech, IR, Schemes (59 notes + 8 hubs) | `study/<subject>/*` | **KEEP → IMPROVE (review)** | Distinct chapters with 900–1,600 words, tables, FAQs and 5 MCQs each. All published on one day, so each needs a factual review pass and a "sources" block before being promoted further |
| Current-affairs topic notes (33) | `study/current-affairs/*` | **KEEP**, 3 pairs to **REVIEW FOR MERGE**, several **IMPROVE** (stale) | Long (1,000–2,600 words) but on one template; 4 sample URLs "duplicate without user-selected canonical" and 2 "crawled – not indexed" |
| Syllabus / exam-pattern posts (5) | `blog/*-syllabus-2025.html` | **IMPROVE (urgent)** | Target the 2025 cycle; exams have moved on |
| Strategy posts (6) | `blog/how-to-*`, `*-vs-*`, `upsc-prelims-attempt-90-questions` | **KEEP / IMPROVE** | Evergreen intent; refresh exam-pattern facts |
| December 2025 CA pair (2) | `blog/current-affairs-dec-2025-summary.html`, `blog/top-25-current-affairs-mcqs-december-2025.html` | **MERGE** | 28% shared 5-gram text, same month, same audience (highest textual overlap on the site) |
| Polity practice pair (2) | `blog/10-most-repeated-…`, `repeated-questions/polity-cheat-code.html` | **KEEP both, DIFFERENTIATE** | 12% overlap. Turn the blog post into a real PYQ page (see N2); keep the cheat code as practice MCQs |
| Cheat codes (11) | `repeated-questions/*` | **IMPROVE** | 500–1,400 words; `english-cheat-code` crawled-not-indexed since June |
| Exam calendar | `exam-calendar.html` | **IMPROVE** | Rebuilt as an official-sources page; add verified dates one exam at a time |
| Utility / legal (contact, privacy, terms) | — | KEEP | — |
| Quiz tool pages | `quiz.html`, `quiz-selector.html`, `result.html` | KEEP **noindex** | Tool UI, no unique crawlable content |

**No page is recommended for removal.** Nothing reviewed was redundant enough to delete. Merges below use 308 redirects to the surviving, closely related page, never to the homepage.

## Topic-cluster map

```
Home (/)
├── Study Portal (/study/index.html)
│   ├── Polity hub ─ 8 chapter notes ─┬─ Polity Cheat Code (practice MCQs)
│   │                                 └─ [N2] UPSC Polity PYQs (official, by topic)
│   ├── History hub ─ 8 notes ────────┬─ History Cheat Code
│   │                                 └─ [N3] UPSC History & Culture PYQs
│   ├── Geography hub ─ 7 notes ──────┬─ Geography Cheat Code · 25 Geography Facts (blog)
│   │                                 └─ [N4] UPSC Geography PYQs
│   ├── Economy hub ─ 6 notes ────────┬─ Economy / Banking Awareness Cheat Codes · Banking Terms (blog)
│   │                                 └─ [N5] UPSC Economy PYQs · Union Budget CA note
│   ├── Environment hub ─ 7 notes ────┬─ Environment Cheat Code · climate / net-zero / carbon-credit CA notes
│   │                                 └─ [N6] UPSC Environment PYQs
│   ├── Science & Tech hub ─ 7 notes ─┬─ Sci-Tech / Computer Cheat Codes · space CA notes
│   │                                 └─ RRB Group D NCERT Science (blog)
│   ├── IR hub ─ 4 notes ─────────────── G20 / BRICS / bilateral CA notes · Static GK Cheat Code
│   ├── Schemes hub ─ 4 notes ────────── Major Schemes 2026 CA note
│   └── Current Affairs hub ─ 33 topic notes ─ [N11] Monthly CA quiz series
├── Exam guides (blog)
│   ├── UPSC: syllabus · attempt strategy · UPSC vs PSC · [N1] Prelims 2026 paper analysis · [N16] CSAT guide
│   ├── SSC: CGL syllabus · 180+ strategy · CGL vs CHSL · [N7] Quant topic sets
│   ├── Bank: syllabus · puzzles · IBPS vs SBI · banking terms · [N8] Reasoning · [N9] DI sets
│   └── Railway / PSC: RRB syllabus · PSC syllabus · NCERT science
├── Cheat Codes hub (/repeated-questions/) ─ 11 subject cheat codes (each links up to its study hub)
└── Exam Calendar (official sources) ─ links to every syllabus guide
```

Linking rules: each chapter note links to its hub and 2–3 sibling chapters. Each hub links to its cheat code (added in this change) and its PYQ page (when built). Each exam guide links to the hubs its syllabus covers. Each cheat code links to its study notes (added in this change).

## Top 20 existing pages to improve

| # | Page | Audience / intent | Suggested title (≤ 65 chars) and format | What to change, and how it will differ | Internal links | Priority and rationale |
|---|---|---|---|---|---|---|
| 1 | `blog/upsc-prelims-syllabus-2025.html` | UPSC aspirants: "UPSC prelims syllabus" (informational, recurring each year) | "UPSC Prelims Syllabus & Exam Pattern (CSE 2027)" · guide + tables | Verify against the CSE 2026 notification; the repo's `pdfs/upsc-syllabus.pdf` is the official text. Add topic-to-notes mapping (each syllabus line links to the matching study note). Keep the URL and add a dated "What changed" box | → all 9 study hubs, CSAT guide (N16), PYQ pages | **Done 2026-10-20** against the CSE 2026 notice (see SEO_AUDIT.md). Re-check when the CSE 2027 notice is out |
| 2 | `blog/ssc-cgl-syllabus-2025.html` | SSC CGL aspirants: syllabus/pattern | "SSC CGL Syllabus & Exam Pattern 2026: Tier 1 & 2" | Re-verify the pattern against the 2026 notice on ssc.gov.in; add marks/sections tables; map sections to notes and cheat codes | → Quant / English cheat codes, Static GK, N7 | **Done 2026-10-20** against the CGL 2026 notice |
| 3 | `blog/bank-exam-syllabus-2025.html` | IBPS/SBI/RBI aspirants | "Bank Exam Syllabus 2026: IBPS PO, SBI PO, RBI Grade B" | Separate tables per exam, sourced from each notification | → banking terms, puzzles, Banking Awareness Cheat Code, N8, N9 | **P0** |
| 4 | `blog/rrb-syllabus-2025.html` | Railway aspirants | "RRB NTPC, Group D & JE Syllabus 2026" | Verify against the latest CEN notices | → RRB NCERT science post, Science hub | **P1** |
| 5 | `blog/psc-syllabus-2025.html` | State PSC aspirants | "UPPSC, MPPSC & TNPSC Syllabus 2026" | One section per commission, each linked to its official site | → Geography facts post, UPSC vs PSC | **P1** |
| 6 | `exam-calendar.html` | Everyone: "exam date" | Keep the current title · table | Add each **2026–27 date only from the official notice**, with a link to that PDF and the date checked | → syllabus posts | **P1.** Trust page with 44 inbound links |
| 7 | `blog/10-most-repeated-upsc-polity-questions-2020-2025.html` | UPSC: "polity PYQ" | Evolve into N2 ("UPSC Prelims Polity PYQs 2015–2025, Topic-wise") | Replace the practice MCQs with **actual** UPSC questions copied from official papers, with the official answer and a why-correct / why-others-wrong explanation. Keep the URL, or 308 it to the new N2 URL if the slug changes | → Polity hub, cheat code | **P1.** High-intent query class; currently only practice items |
| 8 | `repeated-questions/english-cheat-code.html` | SSC/Bank English section | "English Grammar Rules for SSC & Bank: Error Spotting Guide" | Crawled-not-indexed since June. Add worked error-spotting examples per rule and a 15-question practice set with explanations | ← SSC/bank syllabus posts | **P1** |
| 9 | `blog/current-affairs-dec-2025-summary.html` + `blog/top-25-current-affairs-mcqs-december-2025.html` | Monthly CA revision | Merge into "December 2025 Current Affairs: Summary + 25 MCQs" | Merge into the MCQ page (more content); 308 the summary URL to it | → CA hub | **P1.** Highest overlap pair on the site |
| 10 | `study/current-affairs/g20-summit.html` | UPSC GS-2: G20 | "G20: India's 2023 Presidency and What Came After" | Add the 2024 (Brazil), 2025 (South Africa) and 2026 presidencies from official G20 sources; currently stops at 2023 | → IR groupings note, BRICS notes | **P1.** Stale |
| 11 | `study/current-affairs/brics-expansion.html` + `brics-summit-2026-new-delhi.html` | UPSC IR | Review for overlap; keep separate only if intents differ (membership history vs 2026 summit) | Cross-link; remove duplicated background | ↔ each other, IR hub | P2 |
| 12 | `study/current-affairs/chandrayan-updates.html` + `gaganyaan-chandrayaan4-progress-2026.html` | UPSC S&T | Review for overlap; rename the slug typo ("chandrayan") only with a 308 | Consolidate shared ISRO background into the Space & Defence note | → Science hub | P2 |
| 13 | `study/current-affairs/index.html` | UPSC CA hub | "UPSC Current Affairs Notes by Topic (2026)" | Crawled-not-indexed. Add a real intro, group by GS paper, show last-updated per topic, drop "33 Topics" count-bait | → all CA notes | **P1** |
| 14 | `study/current-affairs/deepfake-regulation-in-india.html` | UPSC GS-3 | — | Crawled-not-indexed. Verify against the latest IT Rules amendments; add primary sources (MeitY / Gazette) | → Cybersecurity, DPDP notes | P2 |
| 15 | `study/current-affairs/aditya-l1-mission.html` | UPSC/SSC S&T | — | Crawled-not-indexed. Add mission results since launch from ISRO sources; trim generic text | → Space & Defence note | P2 |
| 16 | `study/current-affairs/union-budget-2026-27.html` | UPSC/Bank economy | Becomes "Union Budget 2027-28" after Feb 1, 2027 | New page for the new budget; keep 2026-27 as an archive linked from it | → Budget & Fiscal Policy note | P2 (time-bound) |
| 17 | `study/current-affairs/major-government-schemes-2026.html` | Scheme questions | — | Overlaps the 4 `study/schemes` notes. Keep only schemes approved in 2026 and link out to the scheme notes for background | → Schemes hub | P2 |
| 18 | `blog/how-to-score-180-ssc-cgl-tier1.html` | SSC CGL strategy | Drop "(2025)" from the title once the pattern is verified | Verify marks and sections against the current notice | → SSC syllabus, N7 | **Done 2026-10-20** (sectional-timer pacing) |
| 19 | Study hubs (`study/*/index.html`, 9 pages; 2 flagged "duplicate") | Subject-level intent ("polity notes for UPSC") | Keep titles · hub pages | Add a 150–250 word original overview per hub ("how this subject is tested, where to start") and a chapter order | → chapters, cheat code, PYQs | **P1.** Hubs are only 186–306 words |
| 20 | All 59 study notes (batch review) | — | Shorten titles to ≤ 65 chars when edited | Add a **Sources** block (NCERT chapter / Constitution article / official site) and a "Reviewed on" date to each note as it is fact-checked | — | **P1** ongoing. Mitigates H4 |

## Top 20 new content opportunities

Each must be original, sourced and useful on its own. None is a templated variant of an existing page. The "why it's distinct" column states the differentiation; demand is a **hypothesis to validate in Search Console** after launch.

| # | Proposed page | Audience / intent | Suggested title and format | Why it's distinct from existing content | Links | Priority |
|---|---|---|---|---|---|---|
| N1 | UPSC Prelims 2026 GS-I paper analysis | UPSC aspirants reviewing the 2026 paper | "UPSC Prelims 2026 GS Paper 1: Subject-wise Analysis" · table + commentary | No existing page analyses an actual paper. Source: the official question paper on upsc.gov.in; answers only from UPSC's official key when published | → hubs, PYQ pages | P1 |
| N2 | Polity PYQs by topic | UPSC | "UPSC Prelims Polity PYQs (2015–2025) by Topic, with Explanations" | Real questions with official citations (paper year + Q no.); explanations for every option | ↔ Polity hub, cheat code (replaces item 7 framing) | **P1** |
| N3 | History & Art-Culture PYQs | UPSC | Same format | Same | ↔ History hub | P2 |
| N4 | Geography PYQs | UPSC | Same format | Same | ↔ Geography hub | P2 |
| N5 | Economy PYQs | UPSC | Same format | Same | ↔ Economy hub | P2 |
| N6 | Environment PYQs | UPSC | Same format | Same | ↔ Environment hub | P2 |
| N7 | Percentages: worked examples + practice set | SSC CGL/CHSL quant | "Percentage Questions for SSC: Methods, Shortcuts & 30 Solved Examples" | No quant study notes exist (only a formula cheat code and a JSON quiz bank) | ← SSC syllabus, Quant cheat code | P1 |
| N8 | Seating arrangement & syllogism guide | Bank prelims reasoning | "Syllogism for Bank Exams: Rules, Venn Method & Solved Questions" | No reasoning notes exist; the puzzles post covers only 5 types | ← Bank syllabus, puzzles post | P1 |
| N9 | Data Interpretation practice sets | IBPS/SBI mains | "Data Interpretation Practice for Bank Exams (Tables, Bar, Pie)" with fully worked solutions | No DI content exists | ← Bank syllabus | P2 |
| N10 | English error spotting rules | SSC/Bank | Could be the expanded item 8 rather than a new page | Avoid a duplicate: build it **into** the English cheat code | — | (merged into #8) |
| N11 | Monthly current-affairs quiz (Oct 2026 onward) | All exams | "October 2026 Current Affairs Quiz: 25 MCQs with Sources" | Each fact cited to PIB / official releases; one page per month, linked from the CA hub | ← CA hub, homepage | P1 (recurring) |
| N12 | Important Constitutional Amendments table | UPSC/SSC polity | "Important Constitutional Amendments of India: 1st to 106th (Table)" | Quick-reference table; the chapter notes mention amendments only in passing | ↔ Polity notes | P2 |
| N13 | Important Articles quick reference | UPSC/SSC | "Important Articles of the Indian Constitution: Part-wise Table" | Lookup format, not prose | ↔ Polity hub | P2 |
| N14 | National parks and tiger reserves by state | SSC/PSC static GK | "National Parks & Tiger Reserves of India by State (Table)" | Table + map links; sourced to MoEFCC / NTCA lists | ↔ Environment, Geography | P2 |
| N15 | Static GK printable PDFs | All | Rebuild `pdfs/ssc-gk-2025.pdf` as a verified, dated revision sheet | The existing PDF is unsourced plain text | ← homepage materials | P3 |
| N16 | CSAT guide | UPSC Paper II | "UPSC CSAT: Qualifying Marks, Syllabus & Preparation Plan" | Only the GS paper is covered today | ← UPSC syllabus | P2 |
| N17 | SSC CGL 2026 notification explainer | SSC | Publish only once the notice is out, with a link to the PDF | Time-bound, notice-based | ← SSC syllabus, calendar | P2 (event) |
| N18 | IBPS PO 2026 notification explainer | Bank | Same pattern | Same | ← Bank syllabus, calendar | P2 (event) |
| N19 | Printable one-page revision sheets per study hub | All | "Polity Revision Sheet (Printable)" etc., as HTML with print CSS | Uses the existing print button; condensed from reviewed notes only | ← each hub | P3 |
| N20 | About & editorial policy | Trust | "About AspirantDaily: Who We Are & How We Check Facts" | Real ownership, contact on the site's own domain, correction policy. **Needs owner input; no fabricated credentials** | Footer site-wide | **P1** (trust) |

## Writing standard for every new or improved page

- A learning objective at the top. Original explanations, a worked example or table, and a short quiz with **why the answer is right and why each distractor is wrong**.
- Every factual claim about schemes, dates, numbers or exams cites a primary source (official notification, PIB, Gazette, NCERT, upsc.gov.in). Previous-year questions only from official papers, with year and question number. Answer keys only from the official key.
- `datePublished` = first publication. Visible "Last updated" and `dateModified` change only on substantive edits. `scripts/build_sitemap.py` derives `lastmod` the same way.
- No visible keyword lists, no "guaranteed" claims, no fabricated authors or reviews.
