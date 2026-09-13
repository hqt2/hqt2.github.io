#!/usr/bin/env python3
"""
watch_notes.py — watch notes_inbox/ for new PDF files and publish each one
straight onto the Notes page.

Usage:
    python3 watch_notes.py

Leave this running in a Terminal window. Whenever you drop (save,
drag-and-drop, or move) a .pdf file into notes_inbox/, the script:
  1. waits until the file is done being written (size stops changing),
  2. asks you, right there in the terminal, for a short one-line note
     describing the file,
  3. moves the PDF into assets/notes/<safe-name>.pdf,
  4. adds a new entry at the top of the "Lecture notes" list on
     notes.html, using what you typed as the link text.

It only touches local files — nothing is pushed to GitHub automatically.
After adding note(s) you're happy with, publish them the usual way:

    git add -A
    git commit -m "Add note: <description>"
    git push

Press Ctrl+C to stop watching.
"""
import re
import sys
import time
import shutil
import unicodedata
from pathlib import Path
from datetime import datetime

SITE_ROOT = Path(__file__).resolve().parent
NOTES_INBOX = SITE_ROOT / "notes_inbox"
NOTES_PDF_DIR = SITE_ROOT / "assets" / "notes"
NOTES_HTML = SITE_ROOT / "notes.html"

POLL_SECONDS = 2
STABLE_CHECKS = 2   # how many consecutive stable size readings before we act


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def slugify(name: str) -> str:
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = name.lower()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name).strip("-")
    return name or "note"


MAX_WAIT_SECONDS = 30


def wait_until_stable(path: Path) -> bool:
    """Return True once the file's size has stopped changing across
    STABLE_CHECKS consecutive polls (guards against reading a file that's
    still being copied/saved). Return False if the file disappeared or
    never stabilized within MAX_WAIT_SECONDS."""
    last_size = -1
    stable_count = 0
    waited = 0
    while stable_count < STABLE_CHECKS:
        if not path.exists():
            return False
        size = path.stat().st_size
        if size == last_size and size > 0:
            stable_count += 1
        else:
            stable_count = 0
        last_size = size
        time.sleep(1)
        waited += 1
        if waited >= MAX_WAIT_SECONDS:
            print(f"  Warning: {path.name} hasn't finished writing after "
                  f"{MAX_WAIT_SECONDS}s — skipping for now, will retry next poll.")
            return False
    return True


def unique_pdf_path(base_slug: str) -> Path:
    candidate = NOTES_PDF_DIR / f"{base_slug}.pdf"
    n = 2
    while candidate.exists():
        candidate = NOTES_PDF_DIR / f"{base_slug}-{n}.pdf"
        n += 1
    return candidate


def insert_note_entry(title: str, href: str, caption: str):
    content = read(NOTES_HTML)
    ul_re = re.compile(r'(<ul class="linklist">)(.*?)(</ul>)', re.DOTALL)
    m = ul_re.search(content)
    if not m:
        sys.exit('Could not find <ul class="linklist"> in notes.html.')

    new_li = (
        f'    <li>\n'
        f'      <p><a href="{href}">{title}</a></p>\n'
        f'      <p class="url">{caption}</p>\n'
        f'    </li>'
    )

    items = re.findall(r'<li>.*?</li>', m.group(2), flags=re.DOTALL)
    items = [item.strip() for item in items]
    items.insert(0, new_li.strip())   # most recent note first
    new_inner = "\n    " + "\n    ".join(items) + "\n  "
    new_content = content[:m.start()] + m.group(1) + new_inner + m.group(3) + content[m.end():]
    write(NOTES_HTML, new_content)


def process_pdf(pdf_path: Path):
    print(f'\nNew file detected: {pdf_path.name}')
    if not wait_until_stable(pdf_path):
        print("  (file disappeared before it finished saving — skipped)")
        return

    try:
        description = input(f'  Ghi chú ngắn cho "{pdf_path.name}" (sẽ dùng làm tên link): ').strip()
    except EOFError:
        description = ""
    if not description:
        description = pdf_path.stem

    base_slug = slugify(pdf_path.stem)
    dest = unique_pdf_path(base_slug)
    NOTES_PDF_DIR.mkdir(parents=True, exist_ok=True)
    shutil.move(str(pdf_path), str(dest))

    rel_href = f"assets/notes/{dest.name}"
    today = datetime.now().strftime("%B %-d, %Y") if sys.platform != "win32" else datetime.now().strftime("%B %d, %Y")
    caption = f"PDF, added {today}."
    insert_note_entry(description, rel_href, caption)

    print(f"  Saved to {rel_href}")
    print(f'  Added to notes.html: "{description}"')
    print("  When ready, publish with:\n    git add -A\n    git commit -m \"Add note: " + description + "\"\n    git push")


def main():
    NOTES_INBOX.mkdir(parents=True, exist_ok=True)
    NOTES_PDF_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Watching {NOTES_INBOX} for new PDF files. Press Ctrl+C to stop.")

    try:
        while True:
            candidates = {p for p in NOTES_INBOX.iterdir()
                          if p.is_file() and p.suffix.lower() == ".pdf" and not p.name.startswith(".")}
            for path in sorted(candidates):
                process_pdf(path)   # moves the file away on success; left in place to retry otherwise
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped watching.")


if __name__ == "__main__":
    main()
