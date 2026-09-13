#!/usr/bin/env python3
"""
delete_post.py — remove a blog post from hqt2.github.io cleanly: deletes
posts/<slug>.html, removes its entry from blog.html and index.html,
re-wires the prev/next navigation links on the posts before and after
it, and also removes the matching drafts/<slug>.md if new_post.py
archived one there.

Usage:
    python3 delete_post.py my-old-post
    python3 delete_post.py posts/my-old-post.html   (also accepted)

Run this from the site's repo root (the folder that contains posts/,
blog.html, index.html).
"""
import re
import sys
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent
POSTS_DIR = SITE_ROOT / "posts"
DRAFTS_DIR = SITE_ROOT / "drafts"
BLOG_HTML = SITE_ROOT / "blog.html"
INDEX_HTML = SITE_ROOT / "index.html"


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
    """Existing blog.html entries, newest first, in file order."""
    content = read(BLOG_HTML)
    entries = []
    for m in ENTRY_RE.finditer(content):
        entries.append({"slug": m.group(1), "title": m.group(2)})
    return entries


def remove_li_for_slug(content: str, slug: str):
    pattern = re.compile(
        r'[ \t]*<li>\s*<a class="entry-title" href="posts/' + re.escape(slug) + r'".*?</li>\n?',
        re.DOTALL,
    )
    new_content, n = pattern.subn("", content)
    return new_content, n


def update_prev_next(order_slugs):
    """order_slugs: remaining post filenames, newest first (post already removed)."""
    titles = {}
    for s in order_slugs:
        p = POSTS_DIR / s
        if p.exists():
            mt = re.search(r"<h1>(.*?)</h1>", read(p))
            if mt:
                titles[s] = mt.group(1)

    for i, slug in enumerate(order_slugs):
        path = POSTS_DIR / slug
        if not path.exists():
            continue
        content = read(path)

        newer = order_slugs[i - 1] if i > 0 else None
        older = order_slugs[i + 1] if i < len(order_slugs) - 1 else None

        def link_or_span(target_slug, arrow):
            if target_slug is None:
                return "<span></span>"
            title = titles.get(target_slug, target_slug)
            if arrow == "older":
                return f'<a href="{target_slug}">← {title}</a>'
            return f'<a href="{target_slug}">{title} →</a>'

        older_html = link_or_span(older, "older")
        newer_html = link_or_span(newer, "newer")

        nav_re = re.compile(r'<nav class="post-nav">.*?</nav>', re.DOTALL)
        new_nav = f'<nav class="post-nav">\n    {older_html}\n    {newer_html}\n  </nav>'
        content, n = nav_re.subn(lambda m: new_nav, content, count=1)
        if n:
            write(path, content)


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 delete_post.py <slug-or-filename>")

    arg = sys.argv[1]
    arg = arg.split("/")[-1]  # drop a leading "posts/" if given
    if not arg.endswith(".html"):
        arg += ".html"
    slug = arg

    post_path = POSTS_DIR / slug
    if not post_path.exists():
        sys.exit(f"posts/{slug} does not exist. Nothing to delete.")

    slug_base = slug[:-len(".html")]
    draft_path = DRAFTS_DIR / f"{slug_base}.md"
    has_draft = draft_path.exists()

    # confirm
    title_match = re.search(r"<h1>(.*?)</h1>", read(post_path))
    title = title_match.group(1) if title_match else slug
    draft_note = f" and its draft (drafts/{slug_base}.md)" if has_draft else ""
    answer = input(f'This will permanently delete "{title}" (posts/{slug}){draft_note} '
                    f'and remove it from Blog/Home. Continue? [y/N] ').strip().lower()
    if answer != "y":
        print("Aborted, nothing changed.")
        return

    # 1. remove from blog.html
    blog_content = read(BLOG_HTML)
    blog_content, n1 = remove_li_for_slug(blog_content, slug)
    if n1:
        write(BLOG_HTML, blog_content)
        print("Removed entry from blog.html")
    else:
        print("Warning: entry not found in blog.html (continuing)")

    # 2. remove from index.html "Latest blog posts", if present
    index_content = read(INDEX_HTML)
    index_content, n2 = remove_li_for_slug(index_content, slug)
    if n2:
        # backfill index.html's top-3 list from blog.html's remaining order
        entries = list_blog_entries()
        remaining = [e for e in entries if e["slug"] != slug]
        # only need to top up if index.html now has fewer than 3 entries
        ul_re = re.compile(r'(<ul class="entries">)(.*?)(</ul>)', re.DOTALL)
        m = ul_re.search(index_content)
        current_items = re.findall(r'<li>.*?</li>', m.group(2), flags=re.DOTALL)
        if len(current_items) < 3 and len(current_items) < len(remaining):
            have_slugs = set(re.findall(r'href="posts/([^"]+)"', m.group(2)))
            for e in remaining:
                if len(current_items) >= 3:
                    break
                if e["slug"] in have_slugs:
                    continue
                # pull this entry verbatim from blog.html to keep formatting identical
                blog_entry_m = re.search(
                    r'<li>\s*<a class="entry-title" href="posts/' + re.escape(e["slug"]) + r'".*?</li>',
                    read(BLOG_HTML), re.DOTALL,
                )
                if not blog_entry_m:
                    continue
                # index.html entries omit the <p class="entry-note"> line
                li_no_note = re.sub(r'\s*<p class="entry-note">.*?</p>', "", blog_entry_m.group(0), flags=re.DOTALL)
                current_items.append(li_no_note.strip())
                have_slugs.add(e["slug"])
        new_inner = "\n    " + "\n    ".join(item.strip() for item in current_items) + "\n  "
        index_content = index_content[:m.start()] + m.group(1) + new_inner + m.group(3) + index_content[m.end():]
        print("Removed entry from index.html (backfilled Latest blog posts)")
    write(INDEX_HTML, index_content)

    # 3. delete the post file itself
    post_path.unlink()
    print(f"Deleted posts/{slug}")

    # 3b. delete the matching draft, if one was archived by new_post.py
    if has_draft:
        draft_path.unlink()
        print(f"Deleted drafts/{slug_base}.md")

    # 4. fix prev/next chain for remaining posts
    entries = list_blog_entries()
    order_slugs = [e["slug"] for e in entries]
    update_prev_next(order_slugs)
    print("Fixed prev/next links across remaining posts")

    print(f'\nDone. Review the changes, then:\n  git add -A\n  git commit -m "Remove post: {title}"\n  git push')


if __name__ == "__main__":
    main()
