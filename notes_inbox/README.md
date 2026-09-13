# notes_inbox/

Drop PDF files here while `watch_notes.py` is running (see the script's
docstring, or run `python3 watch_notes.py` from the repo root). Each
PDF is picked up automatically:

1. The script waits until the file is fully written.
2. It asks you, in the terminal, for a short one-line description.
3. It moves the file into `assets/notes/` and adds it to the top of
   the "Lecture notes" list on `notes.html`.

Nothing is pushed to GitHub automatically — publish with the usual
`git add -A && git commit -m "..." && git push` once you're happy
with what's been added.
