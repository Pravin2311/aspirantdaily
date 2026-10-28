"""Build the indexable MCQ practice pages (practice/*.html) from the quiz question bank.

The daily quiz (quiz.html) is noindex, so search engines never saw the question bank.
These pages show every question of a subject with its answer and explanation behind
a "Show answer" toggle, in English with a Hindi switch. Current affairs is left out
because its answers go stale; it stays in the daily quiz only.

Run after any change to data/*.json (tests fail when the pages are out of date):
    python -X utf8 scripts/build_practice.py
"""
import html
import json
import os
import sys

from seo_lib import HOST, ROOT

OUT = "practice"
# slug, data file, short name, h1, intro, related notes (path, label)
SUBJECTS = [
    ("quantitative-aptitude-mcqs", "quant", "Quant",
     "Quantitative Aptitude MCQs with Answers",
     "Percentages, profit and loss, simple and compound interest, time and work, speed and distance, "
     "ratios, averages, HCF/LCM, mensuration and basic algebra: the arithmetic every SSC, Bank and RRB "
     "paper tests. Each answer comes with the working.",
     [("study/quant/index.html", "Quantitative Aptitude study notes"),
      ("repeated-questions/quant-cheat-code.html", "Quant Cheat Code: 20 shortcuts")]),
    ("reasoning-mcqs", "reasoning", "Reasoning",
     "Reasoning MCQs with Answers",
     "Number and letter series, coding-decoding, blood relations, direction sense, odd one out, analogies, "
     "calendars, clocks, ranking and syllogisms: the logical reasoning section of SSC, Bank and RRB exams.",
     [("study/reasoning/index.html", "Reasoning study notes")]),
    ("english-mcqs", "english", "English",
     "English Grammar MCQs with Answers",
     "Synonyms, antonyms, idioms, one-word substitutions, spellings, articles, prepositions, tenses, voice, "
     "narration and error spotting: the English section of SSC and Bank exams.",
     [("repeated-questions/english-cheat-code.html", "English Cheat Code: grammar and vocabulary tips")]),
    ("general-science-mcqs", "science", "Science",
     "General Science MCQs with Answers",
     "Physics units and laws, everyday chemistry, the human body, plants and the solar system: the general "
     "science questions asked in SSC, RRB and state PSC papers.",
     [("study/science-tech/index.html", "Science & Tech study notes"),
      ("repeated-questions/science-tech-cheat-code.html", "Science & Tech Cheat Code")]),
    ("geography-mcqs", "geography", "Geography",
     "Geography MCQs with Answers: India and World",
     "World capitals, rivers, mountains, deserts, straits and boundary lines, plus Indian rivers, states and "
     "physical features: the geography asked in SSC, UPSC Prelims and state PSC exams.",
     [("study/geography/index.html", "Geography study notes"),
      ("repeated-questions/geography-cheat-code.html", "Geography Cheat Code")]),
    ("economics-mcqs", "economics", "Economics",
     "Indian Economy MCQs with Answers",
     "Basic economic concepts, money and banking, the RBI, taxes and GST, fiscal policy, planning and "
     "India's economic history: the economy questions in UPSC, Bank and SSC exams.",
     [("study/economy/index.html", "Economy study notes"),
      ("repeated-questions/economy-cheat-code.html", "Economy Cheat Code")]),
    ("static-gk-mcqs", "static-gk", "Static GK",
     "Static GK MCQs with Answers",
     "National symbols, firsts in India, awards, important days, capitals and currencies, and India's "
     "largest and longest: the static general knowledge in SSC, Bank and RRB papers.",
     [("repeated-questions/static-gk-cheat-code.html", "Static GK Cheat Code")]),
    ("computer-awareness-mcqs", "computer", "Computer",
     "Computer Awareness MCQs with Answers",
     "Hardware, memory, software, operating systems, networks, the internet, shortcuts, abbreviations and "
     "number systems: the computer awareness section of Bank and SSC exams.",
     [("study/computer/index.html", "Computer study notes"),
      ("repeated-questions/computer-awareness-cheat-code.html", "Computer Awareness Cheat Code")]),
]
LETTERS = "ABCDEFGH"

STYLE = """  <style>
    .practice-tools { display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: center; margin: 0 0 1.5rem; }
    .lang-toggle { cursor: pointer; }
    .mcq-card details { margin-top: 0.75rem; }
    .mcq-card summary { cursor: pointer; font-weight: 600; color: var(--brand-700, #1d4ed8); }
    .mcq-card details p { margin: 0.5rem 0 0; }
    .hi-t { display: none; }
    html.hi .hi-t { display: revert; }
    html.hi .en-t { display: none; }
  </style>"""

LANG_SCRIPT = """  <script>
    (function () {
      var root = document.documentElement, btn = document.getElementById("lang-toggle");
      function set(hi) {
        root.classList.toggle("hi", hi);
        btn.textContent = hi ? "Show in English" : "हिंदी में देखें";
        btn.setAttribute("aria-pressed", hi ? "true" : "false");
      }
      try { set(localStorage.getItem("practiceLang") === "hi"); } catch (e) { set(false); }
      btn.addEventListener("click", function () {
        var hi = !root.classList.contains("hi");
        set(hi);
        try { localStorage.setItem("practiceLang", hi ? "hi" : "en"); } catch (e) {}
      });
    })();
    function startTimedQuiz(subject) {
      try { localStorage.setItem("practiceContext", JSON.stringify({ subject: subject })); } catch (e) {}
      window.location.href = "/quiz-selector.html";
    }
  </script>"""


def esc(text):
    return html.escape(str(text), quote=True)


def ld(data):
    return ('  <script type="application/ld+json">\n'
            + json.dumps(data, ensure_ascii=False, indent=2) + "\n  </script>")


def head(title, desc, url, schemas, extra=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=optional" rel="stylesheet">
  <link rel="stylesheet" href="/styles.css?v=2">

  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}" />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{url}" />

  <meta property="og:type" content="website" />
  <meta property="og:title" content="{esc(title)}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:image" content="{HOST}/og-image.jpg" />
  <meta name="twitter:card" content="summary_large_image" />

{chr(10).join(ld(s) for s in schemas)}
{extra}
  <!-- Analytics -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-51XLJE4TVH"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-51XLJE4TVH');
  </script>
  <script>/* AdSense only on the production host (not localhost or preview deployments) */(function(){{if(location.hostname!=="www.aspirantdaily.com")return;var a=document.createElement("script");a.async=true;a.src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7495143337429327";a.crossOrigin="anonymous";document.head.appendChild(a);}})();</script>
</head>

<body>

  <header class="site-header">
    <div class="header-inner">
      <a href="/" class="brand-link">
        <span class="brand-logo">AD</span>
        <span class="brand-name">Aspirant<strong>Daily</strong></span>
      </a>
      <nav class="site-nav">
        <a href="/">Home</a>
        <a href="/practice/index.html" class="active">Practice</a>
        <a href="/study/index.html">Study Portal</a>
        <a href="/blog/index.html">Blog</a>
        <a href="/repeated-questions/index.html">Repeated Qs</a>
        <a href="/exam-calendar.html">Exam Calendar</a>
        <a href="/contact.html">Contact</a>
      </nav>
    </div>
  </header>
"""


FOOTER = """
  <footer class="site-footer">
    <div class="footer-inner">
      <div class="footer-brand">
        <a href="/" class="brand-link">
          <span class="brand-logo">AD</span>
          <span class="brand-name">Aspirant<strong>Daily</strong></span>
        </a>
        <p>Free daily MCQ practice for Indian competitive exams.</p>
      </div>
      <nav class="footer-links">
        <a href="/">Home</a>
        <a href="/practice/index.html">Practice MCQs</a>
        <a href="/blog/index.html">Blog</a>
        <a href="/study/index.html">Study Portal</a>
        <a href="/exam-calendar.html">Exam Calendar</a>
        <a href="/contact.html">Contact</a>
      </nav>
      <nav class="footer-links">
        <a href="/privacy-policy.html">Privacy Policy</a>
        <a href="/terms.html">Terms of Service</a>
      </nav>
    </div>
    <p class="footer-copyright">© 2026 AspirantDaily.com</p>
  </footer>
"""


def both(en, hi, tag="span"):
    """English and Hindi versions of one piece of text; CSS shows one of them."""
    if not hi or hi == en:
        return esc(en)
    return f'<{tag} class="en-t">{esc(en)}</{tag}><{tag} class="hi-t" lang="hi">{esc(hi)}</{tag}>'


def load(data_file):
    with open(os.path.join(ROOT, "data", data_file + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def questions_for(subjects):
    """Questions per subject, each question kept only on the first page that has it."""
    seen, out = set(), {}
    for slug, data_file, *_ in subjects:
        data = load(data_file)
        keep = []
        for q in data["questions"]:
            key = " ".join(q["question"]["en"].lower().split())
            if key not in seen:
                seen.add(key)
                keep.append(q)
        out[slug] = (keep, data.get("last_updated", ""))
    return out


def breadcrumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": name, "item": url}
                                for i, (name, url) in enumerate(items)]}


def subject_page(subject, qs, updated):
    slug, data_file, short, h1, intro, related = subject
    n = len(qs)
    url = f"{HOST}/{OUT}/{slug}.html"
    title = f"{h1} ({n} Questions) | AspirantDaily"
    desc = (f"{n} free {short} practice MCQs for SSC, Bank, RRB and PSC exams, each with the answer and a short "
            f"explanation. English and Hindi, no login.")
    quiz = {"@context": "https://schema.org", "@type": "Quiz", "name": h1, "about": short,
            "url": url, "inLanguage": ["en", "hi"], "educationalLevel": "Competitive exam preparation",
            "dateModified": updated,
            "publisher": {"@type": "Organization", "name": "AspirantDaily", "url": HOST},
            "hasPart": [{"@type": "Question", "eduQuestionType": "Multiple choice", "text": q["question"]["en"],
                         "suggestedAnswer": [{"@type": "Answer", "text": o} for o in q["options"]["en"]
                                             if o != q["answer"]["en"]],
                         "acceptedAnswer": {"@type": "Answer", "text": q["answer"]["en"]}} for q in qs]}
    crumbs = breadcrumbs([("Home", HOST + "/"), ("Practice MCQs", f"{HOST}/{OUT}/index.html"), (h1, url)])

    cards = []
    for i, q in enumerate(qs, 1):
        en_opts, hi_opts = q["options"]["en"], q["options"].get("hi") or q["options"]["en"]
        letter = LETTERS[en_opts.index(q["answer"]["en"])]
        opts = "\n".join(f'          <div class="option">{LETTERS[j]}. {both(o, hi_opts[j] if j < len(hi_opts) else "")}</div>'
                         for j, o in enumerate(en_opts))
        exp = q.get("explanation", {})
        cards.append(f"""      <div class="mcq-card" id="q{i}">
        <h3><span class="mcq-number">{i}</span> {both(q["question"]["en"], q["question"].get("hi"))}</h3>
        <div class="options">
{opts}
        </div>
        <details>
          <summary>Show answer</summary>
          <p class="answer">Answer: {letter}. {both(q["answer"]["en"], q["answer"].get("hi"))}</p>
          <p>{both(exp.get("en", ""), exp.get("hi"))}</p>
        </details>
      </div>""")

    others = "\n".join(f'      <li><a href="{s[0]}.html">{esc(s[3])}</a></li>' for s in SUBJECTS if s[0] != slug)
    notes = "\n".join(f'      <li><a href="/{p}">{esc(label)}</a></li>' for p, label in related)
    return head(title, desc, url, [crumbs, quiz], STYLE) + f"""
  <div class="page-header">
    <div class="breadcrumb"><a href="/">Home</a> / <a href="index.html">Practice MCQs</a> / <span>{esc(short)}</span></div>
    <h1>{esc(h1)}</h1>
    <p>{esc(intro)}</p>
  </div>

<main class="container mt-lg">

  <div class="practice-tools">
    <button type="button" id="lang-toggle" class="btn secondary lang-toggle" aria-pressed="false">हिंदी में देखें</button>
    <button type="button" class="btn primary" onclick="startTimedQuiz('{data_file}')">Take a timed {esc(short)} quiz</button>
  </div>

  <p>{n} questions. Try each one before you open its answer. These are practice questions written for
  AspirantDaily, not reproductions of past exam papers. Question bank last updated {esc(updated)}.</p>

  <section class="mcq-list">
{chr(10).join(cards)}
  </section>

  <section class="content-box" style="margin:2rem 0">
    <h2 style="font-size:1.15rem">Revise the topics</h2>
    <ul class="bullet-list">
{notes}
    </ul>
    <h2 style="font-size:1.15rem">More practice MCQs</h2>
    <ul class="bullet-list">
{others}
    </ul>
    <p>Found a wrong answer? <a href="/contact.html">Report it</a> and we will correct it.</p>
  </section>

</main>
{FOOTER}
{LANG_SCRIPT}

</body>
</html>
"""


def index_page(counts):
    url = f"{HOST}/{OUT}/index.html"
    total = sum(counts.values())
    title = "Free Practice MCQs with Answers: SSC, Bank, RRB | AspirantDaily"
    desc = (f"{total} free practice MCQs with answers and explanations in {len(SUBJECTS)} subjects: quant, reasoning, "
            "English, GK, science, geography, economy and computers. English and Hindi.")
    collection = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Practice MCQs with Answers",
                  "url": url, "description": desc,
                  "hasPart": [{"@type": "Quiz", "name": s[3], "url": f"{HOST}/{OUT}/{s[0]}.html"} for s in SUBJECTS]}
    crumbs = breadcrumbs([("Home", HOST + "/"), ("Practice MCQs", url)])
    cards = "\n".join(f"""    <a href="{s[0]}.html" class="blog-card">
      <h3>{esc(s[3])}</h3>
      <p>{counts[s[0]]} questions with answers and explanations.</p>
      <span class="blog-tag">{esc(s[2])}</span>
    </a>""" for s in SUBJECTS)
    return head(title, desc, url, [crumbs, collection]) + f"""
  <div class="page-header">
    <h1>Practice MCQs with Answers</h1>
    <p>{total} free multiple-choice questions for SSC, Bank, RRB and state PSC exams, sorted by subject. Every
    question has its answer and a short explanation, in English and Hindi. No login.</p>
  </div>

<main class="container mt-lg">

  <section class="blog-grid">
{cards}
  </section>

  <section class="content-box" style="margin:2rem 0">
    <h2 style="font-size:1.15rem">Want a timed test instead?</h2>
    <p>The <a href="/quiz.html?exam=mixed">daily mixed quiz</a> gives you a fresh set every day with a timer and a
    score. For subject notes, see the <a href="/study/index.html">Study Portal</a>; for quick revision, the
    <a href="/repeated-questions/index.html">cheat codes</a>.</p>
  </section>

</main>
{FOOTER}
</body>
</html>
"""


def build():
    """Return {site-relative path: html} for every practice page."""
    qs = questions_for(SUBJECTS)
    pages = {f"{OUT}/{s[0]}.html": subject_page(s, *qs[s[0]]) for s in SUBJECTS}
    pages[f"{OUT}/index.html"] = index_page({slug: len(v[0]) for slug, v in qs.items()})
    return pages


def main():
    pages = build()
    for rel, text in pages.items():
        full = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    print(f"wrote {len(pages)} practice pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
