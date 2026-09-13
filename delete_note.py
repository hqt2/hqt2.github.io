#!/usr/bin/env python3
"""
delete_note.py — remove an entry from the Notes page (notes.html), the
symmetric counterpart to watch_notes.py (which adds them).

Usage:
    python3 delete_note.py            # interactive: pick from a numbered list
    python3 delete_note.py 2          # delete note #2 directly (still confirms)
    python3 delete_note.py "heisenberg"   # delete the note whose title/link
                                           # text contains this text (case-
                                           # insensitive; still confirms)

If the note links to a local PDF (assets/notes/...pdf), that file is deleted
too. If it links elsewhere (e.g. a Google Drive URL), only the entry on the
page is removed.

Run this from the site's repo root (the folder that contains notes.html).
"""
import re
import sys
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent
NOTES_HTML = SITE_ROOT / "notes.html"

LI_RE = re.compile(r'<li>\s*<p><a href="([^"]+)">([^<]*)</a></p>(?:\s*<p class="url">([^<]*)</p>)?\s*</li>', re.DOTALL)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def get_list_block():
    content = read(NOTES_HTML)
    ul_re = re.compile(r'(<ul class="linklist">)(.*?)(</ul>)', re.DOTALL)
    m = ul_re.search(content)
    if not m:
        sys.exit('Could not find <ul class="linklist"> in notes.html.')
    return content, m


def list_notes(inner: str):
    """Return list of dicts: href, title, caption, raw (the whole <li>...</li>)."""
    notes = []
    for m in LI_RE.finditer(inner):
        notes.append({
            "href": m.group(1),
            "title": m.group(2),
            "caption": m.group(3) or "",
            "raw": m.group(0),
        })
    return notes


def print_notes(notes):
    print("\nCurrent notes (newest/top first):")
    for i, n in enumerate(notes, start=1):
        extra = f"  [{n['caption']}]" if n["caption"] else ""
        print(f"  {i}. {n['title']}  ->  {n['href']}{extra}")
    print()


def pick_note(notes, arg):
    if arg is None:
        print_notes(notes)
        raw = input(f"Enter the number of the note to delete (1-{len(notes)}), or blank to cancel: ").strip()
        if not raw:
            return None
        if not raw.isdigit() or not (1 <= int(raw) <= len(notes)):
            sys.exit("Invalid selection.")
        return notes[int(raw) - 1]

    if arg.isdigit():
        idx = int(arg)
        if not (1 <= idx <= len(notes)):
            sys.exit(f"No note #{idx}. There are {len(notes)} notes.")
        return notes[idx - 1]

    # text search, case-insensitive, over title and href
    needle = arg.lower()
    matches = [n for n in notes if needle in n["title"].lower() or needle in n["href"].lower()]
    if not matches:
        sys.exit(f'No note matches "{arg}".')
    if len(matches) > 1:
        print(f'Multiple notes match "{arg}":')
        print_notes(matches)
        sys.exit("Be more specific, or pass the number instead.")
    return matches[0]


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None

    content, m = get_list_block()
    notes = list_notes(m.group(2))
    if not notes:
        sys.exit("No notes found on notes.html.")

    note = pick_note(notes, arg)
    if note is None:
        print("Cancelled, nothing changed.")
        return

    is_local_pdf = note["href"].startswith("assets/notes/") and note["href"].lower().endswith(".pdf")
    pdf_path = SITE_ROOT / note["href"] if is_local_pdf else None
    file_note = f" and delete the file ({note['href']})" if is_local_pdf else " (the link is external, no local file to delete)"

    answer = input(f'This will remove "{note["title"]}" from notes.html{file_note}. Continue? [y/N] ').strip().lower()
    if answer != "y":
        print("Aborted, nothing changed.")
        return

    # remove the <li> from the list, keeping the rest of the formatting intact
    inner = m.group(2)
    new_inner = inner.replace(note["raw"], "", 1)
    # tidy up leftover blank lines from the removal
    new_inner = re.sub(r'\n[ \t]*\n(?=[ \t]*<li>)', '\n', new_inner)
    new_content = content[:m.start()] + m.group(1) + new_inner + m.group(3) + content[m.end():]
    write(NOTES_HTML, new_content)
    print(f'Removed "{note["title"]}" from notes.html')

    if is_local_pdf:
        if pdf_path.exists():
            pdf_path.unlink()
            print(f"Deleted {note['href']}")
        else:
            print(f"Warning: {note['href']} was already missing, nothing to delete there.")

    print(f'\nDone. Review the changes, then:\n  git add -A\n  git commit -m "Remove note: {note["title"]}"\n  git push')


if __name__ == "__main__":
    main()
