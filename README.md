# hqt2.github.io

Personal academic site — plain HTML, no build step, no Jekyll.
Edit a file, commit, push. GitHub Pages serves it as-is.

## Layout

```
index.html            Home
about.html            Contact + biography
research.html         Research description + geometric flows
publications.html     Articles, preprints, thesis
notes.html            Notes index (lecture notes + posts)
links.html            Useful links
404.html              Not-found page

posts/                One HTML file per note
assets/css/site.css   All styling for every page
assets/img/           Images (put profile.jpg here)
.nojekyll             Tells GitHub Pages to serve files verbatim
```

Everything else at the top level (folders like `analysis/`, `topology/`, …)
holds one-line redirect files that forward the old Jekyll URLs to the new
`posts/…` addresses, so links shared before the rebuild keep working.
Don't delete them.

## Editing

**Text on a page** — open the `.html` file, change the words between the tags.

**Colours, fonts, spacing** — `assets/css/site.css`. It is the only
stylesheet; a change there applies to every page at once. The colours are
defined once at the top as variables (`--accent`, `--bg`, `--text`, …) for
both the light and dark themes.

**Navigation menu** — it is repeated in the `<nav class="main">` block of
each page. If you add a page, add the link in all of them.

## Adding a new note

1. Copy any file in `posts/` to `posts/your-new-slug.html`.
2. Change the `<title>`, the `<h1>`, the `<time>` and the tags at the top.
3. Replace the content inside `<div class="post-body">`.
4. Add it to the list in `notes.html` (and, if you want, `index.html`).

Maths works with normal LaTeX: `$...$` inline and `$$...$$` for display.
MathJax is already loaded on every post page.

## Publishing

```bash
git add -A
git commit -m "Update site"
git push
```

The live site refreshes about a minute later at
<https://hqt2.github.io>.

## Images

`assets/img/` holds three photos, all resized for the web and stripped of
their EXIF metadata (the originals carried GPS coordinates of where each
was taken):

| File | Where it appears | Size |
|---|---|---|
| `banner.jpg` | Strip across the top of the home page | 1800 px, 175 KB |
| `profile.jpg` | Portrait on the home page | 800 px, 179 KB |
| `hue-gate.jpg` | Beside the biography on the About page | 800 px, 236 KB |

To swap one out, replace the file at the same name and keep it under
about 250 KB. Phone photos are 5-10 MB straight out of the camera, which
is far too heavy for a web page — resize to 800-1800 px wide first, and
strip the metadata while you are at it.

If a photo is ever missing, the page hides that element instead of showing
a broken image, so nothing looks wrong.

## Still to do

- **Three figures in the open-book post** and the **undergraduate thesis
  PDF** are still loaded from `trqhuy.wordpress.com` — the only things on
  this site hosted somewhere else. They work today, but if that blog ever
  goes away the images and the PDF go with it. Download them into
  `assets/img/` and `assets/`, then change the `src`/`href` to point locally.
