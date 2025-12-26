import re
from pathlib import Path

ROOTS = ["_posts", "_pages"]
EXTS = {".md", ".markdown", ".html"}

# $latex ...$  -> $...$
# cũng xử lý $LaTeX ...$ hoặc $LATEX ...$
pattern = re.compile(r"\$(?:\s*)latex(?:\s+)", re.IGNORECASE)

def process_file(f: Path) -> int:
    s = f.read_text(encoding="utf-8", errors="ignore")
    new_s, n = pattern.subn("$", s)
    if n > 0 and new_s != s:
        bak = f.with_suffix(f.suffix + ".bak")
        if not bak.exists():
            bak.write_text(s, encoding="utf-8")
        f.write_text(new_s, encoding="utf-8")
    return n

total = 0
changed = 0

for root in ROOTS:
    p = Path(root)
    if not p.exists():
        continue
    for f in p.rglob("*"):
        if f.suffix.lower() not in EXTS:
            continue
        n = process_file(f)
        if n:
            changed += 1
            total += n
            print(f"[OK] {f}  removed={n}")

print(f"\nDone. changed_files={changed}, total_removed={total}")
