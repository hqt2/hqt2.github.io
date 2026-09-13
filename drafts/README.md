# drafts/

Markdown source files for blog posts go here. Each file is a draft in
the format `new_post.py` expects (front matter + Markdown body — see
the docstring at the top of `../new_post.py` for the exact format).

Workflow:

```bash
# write drafts/my-new-post.md, then:
python3 new_post.py my-new-post.md
```

`new_post.py` accepts either a path to the file or just its filename
(it looks in this folder automatically). After it successfully
generates the post, it moves the draft here and renames it to match
the post's slug, so `drafts/<slug>.md` and `posts/<slug>.html` always
pair up — that's also how `delete_post.py <slug>` knows to remove the
matching draft when you delete a post.
