#!/usr/bin/env python3
"""One-off script: add a small 'Built with Claude & ChatGPT' credit line to
the footer of every page (and to new_post.py's POST_TEMPLATE so future
posts get it automatically too).

Usage: run from the site root: python3 add_footer_credit.py
"""
import re
import sys
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent

HTML_FILES = [
    "404.html", "about.html", "blog.html", "cv.html", "index.html",
    "links.html", "notes.html", "publications.html", "research.html",
    "posts/exotic-spheres-milnor-is-not-dead.html",
    "posts/open-book-decomposition-of-3-manifolds.html",
    "posts/why-geodesics-should-be-geodesics.html",
]

OLD_SNIPPET = '''    <div>© <span id="yr">2026</span> Trần Quang Huy · Department of Mathematics, UIUC</div>
    <div class="foot-links">'''

NEW_SNIPPET = '''    <div>© <span id="yr">2026</span> Trần Quang Huy · Department of Mathematics, UIUC</div>
    <div class="credit">Built with <a href="https://claude.com">Claude</a> &amp; ChatGPT</div>
    <div class="foot-links">'''


def patch_file(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    if NEW_SNIPPET in content:
        print(f"  {path}: already has the credit line, skipping")
        return False
    if OLD_SNIPPET not in content:
        print(f"  {path}: WARNING — expected footer snippet not found, skipped")
        return False
    content = content.replace(OLD_SNIPPET, NEW_SNIPPET)
    path.write_text(content, encoding="utf-8")
    print(f"  {path}: patched")
    return True


def main():
    changed = 0
    for rel in HTML_FILES:
        p = SITE_ROOT / rel
        if not p.exists():
            print(f"  {rel}: MISSING, skipped")
            continue
        if patch_file(p):
            changed += 1

    # new_post.py's POST_TEMPLATE, so future posts include the credit too
    np = SITE_ROOT / "new_post.py"
    content = np.read_text(encoding="utf-8")
    old = '''    <div>© <span id="yr">2026</span> Trần Quang Huy · Department of Mathematics, UIUC</div>
    <div class="foot-links">'''
    new = '''    <div>© <span id="yr">2026</span> Trần Quang Huy · Department of Mathematics, UIUC</div>
    <div class="credit">Built with <a href="https://claude.com">Claude</a> &amp; ChatGPT</div>
    <div class="foot-links">'''
    if new in content:
        print("  new_post.py: already has the credit line, skipping")
    elif old in content:
        content = content.replace(old, new)
        np.write_text(content, encoding="utf-8")
        print("  new_post.py: patched (POST_TEMPLATE)")
        changed += 1
    else:
        print("  new_post.py: WARNING — expected footer snippet not found, skipped")

    css = SITE_ROOT / "assets" / "css" / "site.css"
    css_content = css.read_text(encoding="utf-8")
    credit_css_marker = ".site-footer .credit {"
    if credit_css_marker in css_content:
        print("  site.css: .credit rules already present, skipping")
    else:
        old_css = '.site-footer .foot-links { display: flex; gap: .9rem; flex-wrap: wrap; margin-left: auto; }'
        new_css = (
            old_css + "\n"
            ".site-footer .credit { color: var(--faint); }\n"
            ".site-footer .credit a { color: inherit; text-decoration: underline; "
            "text-decoration-color: var(--border); }\n"
            ".site-footer .credit a:hover { color: var(--accent); text-decoration-color: var(--accent); }"
        )
        if old_css not in css_content:
            print("  site.css: WARNING — expected .foot-links rule not found, skipped")
        else:
            css_content = css_content.replace(old_css, new_css, 1)
            old_h = 'body { --footer-h: 6.5rem; }   /* footer wraps to two lines on narrow screens */'
            new_h = 'body { --footer-h: 8.5rem; }   /* footer now wraps to three lines on narrow screens */'
            if old_h in css_content:
                css_content = css_content.replace(old_h, new_h, 1)
                print("  site.css: bumped mobile --footer-h for the extra credit line")
            else:
                print("  site.css: WARNING — mobile --footer-h rule not found, left as-is")
            css.write_text(css_content, encoding="utf-8")
            print("  site.css: patched (.credit styling)")
            changed += 1

    print(f"\nDone. {changed} file(s) changed.")


if __name__ == "__main__":
    main()
