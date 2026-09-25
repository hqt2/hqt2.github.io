#!/usr/bin/env python3
"""
new_post.py — turn a Markdown draft into a fully wired-up blog post for
hqt2.github.io: generates posts/<slug>.html from the site's template,
inserts the entry into blog.html and (if recent enough) index.html, and
fixes the prev/next navigation links on its neighboring posts.

Usage:
    python3 new_post.py my-draft.md

Drafts live in drafts/. You can pass either a bare filename (it's
looked up in drafts/ automatically) or a full path to the file. After
a post is generated successfully, the draft is moved into drafts/ and
renamed to drafts/<slug>.md, so it always pairs up with its post at
posts/<slug>.html — delete_post.py uses that pairing to remove the
draft too when a post is deleted.

Draft format (front matter + Markdown body):

    title: My New Post
    date: 2026-09-12
    tags: Topology, Analysis
    ---
    Nội dung bài viết ở đây, viết bằng Markdown thường.

    Công thức toán: $E = mc^2$ hoặc dạng hiển thị:

    $$\\int_0^1 x^2 dx = \\frac{1}{3}$$

    ## Một mục con

    Đoạn văn tiếp theo...

Supported Markdown (deliberately small — matches what the site's
existing posts use):
    - blank-line-separated paragraphs
    - ## Heading            -> <h2>
    - **bold** / *italic*   -> <strong> / <em>
    - [text](url)           -> <a href="url">text</a>
    - > quote               -> <blockquote><p>...</p></blockquote>
    - $...$ and $$...$$     -> passed through untouched for MathJax

Run this from anywhere inside the site's repo root (the folder that
contains posts/, blog.html, index.html).
"""
import re
import sys
import html
import shutil
from pathlib import Path
from datetime import datetime

SITE_ROOT = Path(__file__).resolve().parent
POSTS_DIR = SITE_ROOT / "posts"
DRAFTS_DIR = SITE_ROOT / "drafts"
BLOG_HTML = SITE_ROOT / "blog.html"
INDEX_HTML = SITE_ROOT / "index.html"

MATH_PLACEHOLDER = "\x00MATH{}\x00"


# ---------------------------------------------------------------- parsing --

def parse_draft(path: Path):
    text = path.read_text(encoding="utf-8")
    if "---" not in text:
        sys.exit("Draft must have a '---' line separating front matter from the body.")
    front, body = text.split("---", 1)
    meta = {}
    for line in front.strip().splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        meta[key.strip().lower()] = val.strip()

    for required in ("title", "date"):
        if required not in meta:
            sys.exit(f"Draft is missing required front-matter field: {required}")

    try:
        datetime.strptime(meta["date"], "%Y-%m-%d")
    except ValueError:
        sys.exit("date must be in YYYY-MM-DD format, e.g. 2026-09-12")

    meta["tags"] = [t.strip() for t in meta.get("tags", "").split(",") if t.strip()]
    return meta, body.strip("\n")


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug


def format_date(iso_date: str) -> str:
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    return dt.strftime("%B ") + str(dt.day) + dt.strftime(", %Y")


# ------------------------------------------------------------ md -> html --

def protect_math(text: str):
    spans = []

    def stash(m):
        spans.append(m.group(0))
        return MATH_PLACEHOLDER.format(len(spans) - 1)

    # display math $$...$$ first (greedy across the pair, not across other pairs)
    text = re.sub(r"\$\$.+?\$\$", stash, text, flags=re.DOTALL)
    # inline math $...$ (no line breaks inside)
    text = re.sub(r"\$[^\$\n]+\$", stash, text)
    return text, spans


def restore_math(text: str, spans):
    def unstash(m):
        return spans[int(m.group(1))]
    return re.sub(r"\x00MATH(\d+)\x00", unstash, text)


def inline_md(text: str) -> str:
    # escape raw HTML-significant characters first, math placeholders are
    # immune since they don't contain & < >
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text


def markdown_to_html(body: str) -> str:
    protected, spans = protect_math(body)
    blocks = re.split(r"\n\s*\n", protected.strip())
    html_blocks = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith("## "):
            html_blocks.append(f"<h2>{inline_md(block[3:].strip())}</h2>")
        elif block.startswith("> "):
            quote = "\n".join(l[2:] if l.startswith("> ") else l for l in block.splitlines())
            html_blocks.append(f"<blockquote>\n<p>{inline_md(quote)}</p>\n</blockquote>")
        else:
            html_blocks.append(f"<p>{inline_md(block)}</p>")
    result = "\n\n".join(html_blocks)
    return restore_math(result, spans)


def plain_excerpt(body: str, limit: int) -> str:
    first_block = re.split(r"\n\s*\n", body.strip(), 1)[0]
    first_block = re.sub(r"\$\$.+?\$\$", " ", first_block, flags=re.DOTALL)
    first_block = re.sub(r"\$[^\$\n]+\$", " ", first_block)
    plain = re.sub(r"[*_>#\[\]()]", "", first_block)
    plain = re.sub(r"\s+", " ", plain).strip()
    if len(plain) <= limit:
        return plain
    cut = plain[:limit].rsplit(" ", 1)[0]
    return cut + "…"


# --------------------------------------------------------------- helpers --

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


ENTRY_RE = re.compile(
    r'<li>\s*<a class="entry-title" href="posts/([^"]+\.html)">([^<]*)</a>\s*'
    r'<div class="entry-meta">\s*<time datetime="([^"]+)">([^<]*)</time>'
    r'(?:\s*<span class="dot">·</span><span>([^<]*)</span>)?\s*</div>'
    r'(?:\s*<p class="entry-note">([^<]*)</p>)?\s*</li>',
    re.DOTALL,
)


def list_blog_entries():
    """Return existing blog.html entries as list of dicts, newest first, in file order."""
    content = read(BLOG_HTML)
    entries = []
    for m in ENTRY_RE.finditer(content):
        entries.append({
            "slug": m.group(1),
            "title": m.group(2),
            "iso_date": m.group(3),
            "date_text": m.group(4),
            "tags_text": m.group(5) or "",
        })
    return entries


def build_entry_li(meta, slug, with_note, note_text=None):
    tags_html = ""
    if meta["tags"]:
        tags_html = f'\n        <span class="dot">·</span><span>{" · ".join(html.escape(t) for t in meta["tags"])}</span>'
    note_html = f'\n      <p class="entry-note">{html.escape(note_text)}</p>' if with_note and note_text else ""
    return (
        f'    <li>\n'
        f'      <a class="entry-title" href="posts/{slug}">{html.escape(meta["title"])}</a>\n'
        f'      <div class="entry-meta">\n'
        f'        <time datetime="{meta["date"]}">{format_date(meta["date"])}</time>{tags_html}\n'
        f'      </div>{note_html}\n'
        f'    </li>'
    )


def insert_into_list(content: str, list_class: str, new_li: str, new_iso_date: str):
    """Insert new_li into the <ul class="{list_class}">...</ul> block at the
    chronological position given by new_iso_date (newest first)."""
    ul_re = re.compile(rf'(<ul class="{list_class}">)(.*?)(</ul>)', re.DOTALL)
    m = ul_re.search(content)
    if not m:
        sys.exit(f'Could not find <ul class="{list_class}"> in target file.')
    open_tag, inner, close_tag = m.groups()

    items = re.findall(r'<li>.*?</li>', inner, flags=re.DOTALL)
    dates = re.findall(r'<time datetime="([^"]+)">', inner)

    insert_at = len(items)
    for i, d in enumerate(dates):
        if new_iso_date > d:
            insert_at = i
            break

    items.insert(insert_at, new_li)
    items = [item.strip() for item in items]
    new_inner = "\n    " + "\n    ".join(items) + "\n  "
    return content[:m.start()] + open_tag + new_inner + close_tag + content[m.end():], insert_at


def update_prev_next(order_slugs):
    """order_slugs: list of post filenames (with .html), newest first.
    Rewrite each post's <nav class="post-nav"> to point at its correct
    chronological neighbors."""
    for i, slug in enumerate(order_slugs):
        path = POSTS_DIR / slug
        if not path.exists():
            continue
        content = read(path)

        newer = order_slugs[i - 1] if i > 0 else None
        older = order_slugs[i + 1] if i < len(order_slugs) - 1 else None

        def link_or_span(target_slug, arrow, title_lookup):
            if target_slug is None:
                return "<span></span>"
            title = title_lookup.get(target_slug, target_slug)
            if arrow == "older":
                return f'<a href="{target_slug}">← {title}</a>'
            return f'<a href="{target_slug}">{title} →</a>'

        titles = {}
        for s in order_slugs:
            p = POSTS_DIR / s
            if p.exists():
                mt = re.search(r"<h1>(.*?)</h1>", read(p))
                if mt:
                    titles[s] = mt.group(1)

        older_html = link_or_span(older, "older", titles)
        newer_html = link_or_span(newer, "newer", titles)

        nav_re = re.compile(r'<nav class="post-nav">.*?</nav>', re.DOTALL)
        new_nav = f'<nav class="post-nav">\n    {older_html}\n    {newer_html}\n  </nav>'
        content, n = nav_re.subn(lambda m: new_nav, content, count=1)
        if n:
            write(path, content)


POST_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} · Vietnamese-Illini Math Guy</title>
  <meta name="description" content="{description}">
  <meta name="author" content="Trần Quang Huy">
  <meta property="og:title" content="{title} · Vietnamese-Illini Math Guy">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="website">
  <link rel="canonical" href="https://hqt2.github.io/posts/{slug}">
  <link rel="stylesheet" href="../assets/css/site.css">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>∮</text></svg>">
<script>
  (function () {{
    var root = document.documentElement;
    try {{
      var saved = localStorage.getItem('theme');
      if (saved === 'dark' || saved === 'light') root.setAttribute('data-theme', saved);
    }} catch (e) {{}}
    window.__toggleTheme = function () {{
      var cur = root.getAttribute('data-theme');
      if (!cur) {{
        cur = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }}
      var next = cur === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try {{ localStorage.setItem('theme', next); }} catch (e) {{}}
    }};
  }})();
</script>
<script>
  window.MathJax = {{
    tex: {{
      inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
      displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
      processEscapes: true
    }},
    options: {{ skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'] }}
  }};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="site-header">
  <div class="bar">
    <a class="brand" href="../index.html"><span class="mark">∮</span> Vietnamese-Illini Math Guy</a>
    <nav class="main" aria-label="Main">
        <a href="../index.html">Home</a>
        <a href="../about.html">About</a>
        <a href="../research.html">Research</a>
        <a href="../publications.html">Publications</a>
        <details class="writing-menu is-current"><summary>Writing</summary><div class="writing-links"><a href="../blog.html" aria-current="page">Blog</a><a href="../notes.html">Expository writing</a></div></details>
        <a href="../links.html">Useful links</a>
        <a href="../cv.html">CV</a>
    </nav>
    <button class="theme-toggle" type="button" onclick="window.__toggleTheme()" aria-label="Switch between light and dark theme"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 3a6.4 6.4 0 0 0 9 9A9 9 0 1 1 12 3Z"/><path d="M19 3v4m-2-2h4"/></svg></button>
  </div>
</header>

<main id="main">
<div class="wrap">
  <a class="backlink" href="../blog.html">← All blog posts</a>

  <article>
    <header class="post-header">
      <h1>{title}</h1>
      <div class="post-meta">
        <time datetime="{date}">{date_text}</time>{pills}
      </div>
    </header>

    <div class="post-body">
{body_html}
    </div>
  </article>

  <nav class="post-nav">
    <span></span>
    <span></span>
  </nav>
</div>
</main>

<footer class="site-footer">
  <div class="bar">
    <div>© <span id="yr">2026</span> Trần Quang Huy · Department of Mathematics, UIUC</div>
    <div class="foot-links">
      <a href="mailto:hqt2@illinois.edu">hqt2@illinois.edu</a>
      <a href="../about.html">Contact</a>
      <a href="https://illinois.edu/">Illinois</a>
    </div>
  </div>
</footer>
<script>document.getElementById('yr').textContent = new Date().getFullYear();</script>
</body>
</html>
"""


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 new_post.py <draft.md>")
    draft_path = Path(sys.argv[1])
    if not draft_path.exists():
        # bare filename (or a relative path that doesn't resolve as given) —
        # look it up in drafts/ before giving up
        candidate = DRAFTS_DIR / draft_path.name
        if candidate.exists():
            draft_path = candidate
        else:
            sys.exit(f"File not found: {draft_path} (also checked drafts/{draft_path.name})")

    meta, body = parse_draft(draft_path)
    slug_base = slugify(meta["title"])
    slug = f"{slug_base}.html"
    out_path = POSTS_DIR / slug
    if out_path.exists():
        sys.exit(f"posts/{slug} already exists — pick a different title or delete it first.")

    body_html = markdown_to_html(body)
    description = plain_excerpt(body, 155)
    note_text = plain_excerpt(body, 200)

    pills = ""
    if meta["tags"]:
        pills = "\n        <span class=\"dot\">·</span>" + "".join(
            f'<span class="pill">{html.escape(t)}</span>' for t in meta["tags"]
        )

    post_html = POST_TEMPLATE.format(
        title=html.escape(meta["title"]),
        description=html.escape(description),
        slug=slug,
        date=meta["date"],
        date_text=format_date(meta["date"]),
        pills=pills,
        body_html=body_html,
    )
    write(out_path, post_html)
    print(f"Created posts/{slug}")

    # -- archive the draft as drafts/<slug>.md, so it pairs up with the post --
    DRAFTS_DIR.mkdir(exist_ok=True)
    archived_draft = DRAFTS_DIR / f"{slug_base}.md"
    if draft_path.resolve() != archived_draft.resolve():
        shutil.move(str(draft_path), str(archived_draft))
        print(f"Archived draft to drafts/{slug_base}.md")

    # -- update blog.html (with excerpt) --
    blog_li = build_entry_li(meta, slug, with_note=True, note_text=note_text)
    blog_content = read(BLOG_HTML)
    blog_content, _ = insert_into_list(blog_content, "entries", blog_li, meta["date"])
    write(BLOG_HTML, blog_content)
    print("Updated blog.html")

    # -- update index.html "Latest blog posts" (no excerpt, keep only top 3) --
    index_li = build_entry_li(meta, slug, with_note=False)
    index_content = read(INDEX_HTML)
    index_content, pos = insert_into_list(index_content, "entries", index_li, meta["date"])
    if pos < 3:
        # trim back down to 3 entries
        ul_re = re.compile(r'(<ul class="entries">)(.*?)(</ul>)', re.DOTALL)
        m = ul_re.search(index_content)
        items = re.findall(r'<li>.*?</li>', m.group(2), flags=re.DOTALL)
        items = [item.strip() for item in items[:3]]
        new_inner = "\n    " + "\n    ".join(items) + "\n  "
        index_content = index_content[:m.start()] + m.group(1) + new_inner + m.group(3) + index_content[m.end():]
        write(INDEX_HTML, index_content)
        print("Updated index.html (Latest blog posts)")
    else:
        print("Post is older than the 3 most recent — index.html left unchanged")

    # -- fix prev/next chain across all posts, in the new chronological order --
    entries = list_blog_entries()
    order_slugs = [e["slug"] for e in entries]  # newest first, already includes the new one
    update_prev_next(order_slugs)
    print("Fixed prev/next links across affected posts")

    print(f"\nDone. Review posts/{slug}, then:\n  git add -A\n  git commit -m \"Add post: {meta['title']}\"\n  git push")


if __name__ == "__main__":
    main()
