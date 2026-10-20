"""Render a validated draft into a site page (or a noindex preview).

The page reuses the study-note template: ../styles.css, ../scripts.js
(toggleSection, showAnswer), the same analytics and AdSense tags, Article and
BreadcrumbList JSON-LD (FAQPage only when the FAQ is visible on the page), a
Sources section and a "How this page was prepared" box that states plainly
what was checked by software and what was reviewed by a person.
"""
import html as htmlmod
import json
import os
import re

from content_lib import NEW_HUBS, ROOT
from content_validate import parse_draft, resolve_link
from seo_lib import HOST

HUB_NAMES = {
    "study/polity": "Polity", "study/history": "History", "study/geography": "Geography",
    "study/environment": "Environment", "study/economy": "Economy", "study/science-tech": "Science & Tech",
    "study/current-affairs": "Current Affairs", "study/ir": "International Relations", "study/schemes": "Schemes",
    **{k: v[0] for k, v in NEW_HUBS.items()},
}
NUMBERS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
HEAD_TAGS = """    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=optional" rel="stylesheet">
    <link rel="stylesheet" href="{styles}">
    <!-- Analytics -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-51XLJE4TVH"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'G-51XLJE4TVH');
  </script>
  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7495143337429327"
     crossorigin="anonymous"></script>"""
ANALYTICS_RE = re.compile(r"    <!-- Analytics -->.*?crossorigin=\"anonymous\"></script>", re.S)


def esc(s):
    return htmlmod.escape(s, quote=True)


def rel(from_path, to_path):
    """Relative href from one site path to another."""
    return os.path.relpath(to_path, os.path.dirname(from_path) or ".").replace(os.sep, "/")


def jsonld(obj):
    return ('    <script type="application/ld+json">\n' + json.dumps(obj, indent=2, ensure_ascii=False)
            + "\n    </script>")


def section(n, title, inner):
    num = NUMBERS[n - 1] if n <= len(NUMBERS) else f"{n}."
    return f"""        <section class="study-section collapsible" data-section="{n}">
            <button class="section-header" onclick="toggleSection({n})" aria-expanded="true" aria-controls="section-{n}">
                <span class="section-number">{num}</span>
                <span class="section-title">{esc(title)}</span>
                <span class="toggle-icon">▼</span>
            </button>
            <div class="section-content" id="section-{n}">
                <div class="content-box">
{inner}
                </div>
            </div>
        </section>"""


def mcq_html(mcqs, prefix="q"):
    out = []
    for i, q in enumerate(mcqs, 1):
        qid = f"{prefix}{i}"
        letters = "abcd"
        opts = "\n".join(f'                            <label><input type="radio" name="{qid}" value="{letters[j]}"> '
                         f'({letters[j]}) {esc(o)}</label>' for j, o in enumerate(q["options"]))
        out.append(f"""                    <div class="mcq-item">
                        <p class="mcq-question"><strong>Q{i}.</strong> {esc(q["q"])} <span class="badge badge-secondary">{esc(q["difficulty"])}</span></p>
                        <div class="mcq-options">
{opts}
                        </div>
                        <div class="mcq-answer" id="answer-{qid}">
                            <p><strong>✅ Answer:</strong> ({letters[q["answer"]]}) {esc(q["options"][q["answer"]])}</p>
                            <p><strong>💡 Explanation:</strong> {esc(q["explanation"])}</p>
                        </div>
                        <button class="btn-show-answer" onclick="showAnswer('{qid}')">Show Answer</button>
                    </div>""")
    return "\n".join(out)


def prepared_box(meta, review, n_checks):
    checks = (f"{n_checks} calculations on this page were recomputed by software and matched. " if n_checks else "")
    if review and review.get("status") in ("approved", "published"):
        ed = (f"Reviewed by {esc(review['reviewer'])} on {esc(review['date'])} against the sources listed above"
              f"{' (' + esc(review['scope']) + ')' if review.get('scope') else ''}.")
    else:
        ed = "<strong>Not yet editorially reviewed.</strong> This is a preview; it is not published."
    return f"""                    <div class="highlight-box">
                        <p><strong>How this page was prepared.</strong> Drafted with AI assistance ({esc(meta["drafted_by"])}) from the sources listed above. {checks}Automated checks also covered structure, internal links and duplicate text. Software checks cannot confirm facts. {ed}</p>
                        <p>Found an error? <a href="{{contact}}">Report it</a> and we will correct the page.</p>
                    </div>"""


def strip_check_attrs(body):
    return re.sub(r'\s+data-check="[^"]*"', "", body)


def render(draft_text, plan_row, review=None, preview=False, date_published=None, date_modified=None,
           related_links=None):
    """Return the HTML for the page at plan_row['path'] (or its preview)."""
    meta, sections, _ = parse_draft(draft_text)
    path = plan_row["path"]
    folder = os.path.dirname(path)
    url = HOST + "/" + path
    hub = folder + "/index.html"
    hub_name = HUB_NAMES.get(folder, folder.split("/")[-1].title())
    styles = rel(path, "study/styles.css")
    scripts = rel(path, "study/scripts.js")
    full_title = f"{meta['title']} | AspirantDaily"
    desc = meta["description"]
    date_published = date_published or meta.get("date", "")
    date_modified = date_modified or date_published

    crumbs = [("Home", "index.html")]
    if path.startswith("study/"):
        crumbs.append(("Study Notes", "study/index.html"))
    crumbs += [(hub_name, hub), (meta["h1"], path)]
    ld = [jsonld({
        "@context": "https://schema.org", "@type": "Article", "headline": meta["h1"], "description": desc,
        "image": HOST + "/og-image.jpg",
        "author": {"@type": "Organization", "name": "AspirantDaily", "url": HOST},
        "publisher": {"@type": "Organization", "name": "AspirantDaily",
                      "logo": {"@type": "ImageObject", "url": HOST + "/icons/icon-512.png"}},
        "datePublished": date_published, "dateModified": date_modified,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url}, "articleSection": hub_name,
        "citation": [s["url"] for s in meta["sources"]],
    }), jsonld({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": i, "name": name,
                             "item": HOST if p == "index.html" else HOST + "/" + p}
                            for i, (name, p) in enumerate(crumbs, 1)],
    })]
    faq = meta.get("faq", [])
    if faq:
        ld.append(jsonld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in faq]}))

    blocks = []
    n = 0
    for heading, body in sections:
        n += 1
        blocks.append(section(n, heading, strip_check_attrs(body)))
    if meta.get("mcqs"):
        n += 1
        blocks.append(section(n, f"Practice Questions ({len(meta['mcqs'])})", mcq_html(meta["mcqs"])))
    if faq:
        n += 1
        blocks.append(section(n, "Frequently Asked Questions", "\n".join(
            f"                    <h3>{esc(f['q'])}</h3>\n                    <p>{esc(f['a'])}</p>" for f in faq)))
    n += 1
    src_items = "\n".join(
        f'                        <li><a href="{esc(s["url"])}" rel="noopener">{esc(s["title"])}</a>, {esc(s["publisher"])}'
        f' (accessed {esc(s["accessed"])}). Used for: {esc(s["supports"])}.</li>' for s in meta["sources"])
    n_checks = len(meta.get("checks", []))
    if not src_items:
        src_list = ("                    <p>All problems and solutions on this page are original. No outside facts are "
                    "relied on; every numeric answer is recomputed by software before publishing.</p>\n")
    else:
        src_list = f"                    <ul class=\"bullet-list\">\n{src_items}\n                    </ul>\n"
    sources_inner = (src_list
                     + prepared_box(meta, review, n_checks).replace("{contact}", rel(path, "contact.html")))
    blocks.append(section(n, "Sources and Review", sources_inner))
    if related_links:
        items = "\n".join(f'                        <li><a href="{rel(path, p)}">{esc(t)}</a></li>' for p, t in related_links)
        n += 1
        blocks.append(section(n, "Related Pages", f"                    <ul class=\"bullet-list\">\n{items}\n                    </ul>"))

    crumb_html = " / ".join(f'<a href="{rel(path, p)}">{esc(name)}</a>' for name, p in crumbs[:-1])
    robots = "noindex, nofollow" if preview else "index, follow"
    banner = ('    <div class="highlight-box" style="margin:0;border-radius:0"><strong>DRAFT PREVIEW</strong> — not published, '
              'not indexed, not editorially reviewed unless stated below.</div>\n') if preview else ""
    keywords = meta.get("keywords") or [meta["primary_query"]]
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(full_title)}</title>
    <meta name="description" content="{esc(desc)}">
    <meta name="keywords" content="{esc(', '.join(keywords))}">
    <meta name="robots" content="{robots}">
    <link rel="canonical" href="{url}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{url}">
    <meta property="og:title" content="{esc(full_title)}">
    <meta property="og:description" content="{esc(desc)}">
    <meta property="og:image" content="{HOST}/og-image.jpg">
    <meta name="twitter:card" content="summary_large_image">
{chr(10).join(ld)}
{HEAD_TAGS.format(styles=styles)}
</head>
<body class="study-page">
{banner}    <nav class="study-nav">
        <div class="container">
            <a href="index.html" class="back-link">← Back to {esc(hub_name)}</a>
            <div class="nav-controls">
                <button onclick="toggleAllSections()" class="btn-secondary">Expand/Collapse All</button>
                <button onclick="window.print()" class="btn-primary">📄 Print/Save PDF</button>
            </div>
        </div>
    </nav>

    <header class="page-header">
        <div class="container">
            <div class="breadcrumb">
                {crumb_html} / <span>{esc(meta["h1"])}</span>
            </div>
            <h1>{esc(meta["h1"])}</h1>
            <p class="page-subtitle">{esc(meta["subtitle"])}</p>
            <div class="page-meta">
{chr(10).join(f'                <span class="badge badge-secondary">{esc(e)}</span>' for e in meta["exams"])}
                <span class="badge badge-secondary">📅 Last updated: {esc(date_modified or "draft")}</span>
            </div>
        </div>
    </header>

    <main class="container">

{chr(10).join(blocks)}

        <div class="page-navigation">
            <a href="index.html" class="nav-btn">← {esc(hub_name)}</a>
        </div>
    </main>

    <footer class="page-footer">
        <div class="container">
            <p>Subject: {esc(hub_name)} | Sources are listed on this page. <a href="{rel(path, 'contact.html')}">Report an error</a>.</p>
        </div>
    </footer>

    <script src="{scripts}"></script>
</body>
</html>
"""
    if preview:
        page = relocate_links(page, path, "content/preview/" + path)
    return page


def relocate_links(page, real_path, out_path):
    """Rewrite relative links so a page written to out_path still reaches the real site files
    (or the preview of a sibling draft)."""
    def fix(m):
        attr, href = m.group(1), m.group(2)
        if href.startswith(("http", "#", "/", "mailto:", "data:")):
            return m.group(0)
        frag = ""
        if "#" in href:
            href, frag = href.split("#", 1)
            frag = "#" + frag
        target = resolve_link(href, real_path)
        if target is None:
            return m.group(0)
        if not os.path.exists(os.path.join(ROOT, target)):
            target = "content/preview/" + target
        return f'{attr}="{rel(out_path, target)}{frag}"'
    return re.sub(r'(href|src)="([^"]*)"', fix, page)


def hub_page(folder, title, intro, pages, parent_label="Study Notes", preview=False):
    """A pipeline-generated hub listing published pages: [(path, h1, description)].
    With preview=True it is a noindex copy for content/preview/, listing draft pages."""
    path = folder + "/index.html"
    url = HOST + "/" + path
    up = "study/index.html" if folder.startswith("study/") else "index.html"
    cards = "\n".join(f"""            <a href="{rel(path, p)}" class="topic-card">
                <h2>{esc(h)}</h2>
                <p>{esc(d)}</p>
                <span class="topic-cta">Read →</span>
            </a>""" for p, h, d in pages)
    desc = f"{intro} {len(pages)} page{'s' if len(pages) != 1 else ''}, each with sources and worked examples or practice questions."
    ld = jsonld({"@context": "https://schema.org", "@type": "CollectionPage", "name": title, "description": desc,
                 "url": url, "hasPart": [{"@type": "Article", "name": h, "url": HOST + "/" + p} for p, h, _ in pages]})
    robots = "noindex, nofollow" if preview else "index, follow"
    banner = ('    <div class="highlight-box" style="margin:0;border-radius:0"><strong>DRAFT PREVIEW</strong> — this hub is '
              'created only when its first page is published.</div>\n') if preview else ""
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(title)} Notes and Practice | AspirantDaily</title>
    <meta name="description" content="{esc(desc)}">
    <meta name="robots" content="{robots}">
    <link rel="canonical" href="{url}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{url}">
    <meta property="og:title" content="{esc(title)} Notes and Practice | AspirantDaily">
    <meta property="og:description" content="{esc(desc)}">
    <meta property="og:image" content="{HOST}/og-image.jpg">
{ld}
{HEAD_TAGS.format(styles=rel(path, "study/styles.css"))}
    <style>
        .topic-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.25rem; margin: 2rem 0; }}
        .topic-card {{ display: block; background: var(--card-bg); border: 1px solid var(--border-color); border-top: 4px solid #8b5cf6; border-radius: 12px; padding: 1.5rem; text-decoration: none; color: var(--text-primary); box-shadow: var(--shadow); transition: transform .15s, box-shadow .15s; }}
        .topic-card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow-lg); }}
        .topic-card h2 {{ font-size: 1.15rem; margin: .5rem 0; }}
        .topic-card p {{ color: var(--text-secondary); font-size: .92rem; }}
        .topic-cta {{ display: inline-block; margin-top: .9rem; font-weight: 600; color: var(--primary-color); font-size: .9rem; }}
        .hub-intro {{ max-width: 720px; margin: 1rem auto 0; color: var(--text-secondary); }}
    </style>
</head>
<body class="study-page">
{banner}    <nav class="study-nav">
        <div class="container">
            <a href="{rel(path, up)}" class="back-link">← {esc(parent_label)}</a>
        </div>
    </nav>
    <header class="page-header">
        <div class="container">
            <div class="breadcrumb"><a href="{rel(path, 'index.html')}">Home</a> / <a href="{rel(path, up)}">{esc(parent_label)}</a> / <span>{esc(title)}</span></div>
            <h1>{esc(title)}</h1>
            <p class="hub-intro">{esc(intro)}</p>
        </div>
    </header>
    <main class="container">
        <div class="topic-grid">
{cards}
        </div>
    </main>
    <footer class="page-footer">
        <div class="container"><p>© 2026 AspirantDaily.com</p></div>
    </footer>
</body>
</html>
"""
    return relocate_links(page, path, "content/preview/" + path) if preview else page
