# Content format and publishing

[简体中文](CONTENT.zh-CN.md) · **English**

Real content lives in the Git-ignored `publications/` directory at the repository root. Run `python3 blog/init_content.py` to create draft templates without overwriting existing files.

Use one folder per entry: `publications/articles/my-first-post/` or `publications/projects/my-project/`. Copy the corresponding `_template`, then rename it with lowercase letters, digits, and hyphens. Titles may use any language. Article URLs use `/posts/<name>/`; projects use `/projects/<name>/`. Renaming changes the URL.

## Metadata

```json
{
  "title": "My project",
  "date": "2026-10-19",
  "category": "Notes",
  "subtitle": "A short subtitle",
  "tags": ["Python", "Personal project"],
  "order": 10,
  "image_fit": "contain",
  "published": false
}
```

Title and an ISO date (`YYYY-MM-DD`) are required. Articles sort newest first; projects sort by ascending order, default 100. Category is for articles; subtitle is for projects. Image fit is cover (default, cropped) or contain (fully visible). Templates are drafts. Set published to true when ready; omitting it also means published. The date does not schedule publication.

## Entry files

| File | Purpose |
| --- | --- |
| `summary.md` | A short introduction for cards and the detail header; one to three sentences is usually enough |
| `content.md` | Detailed text |
| `content.en.md` | Optional English version |
| `link.txt` | One complete HTTP(S) URL; optional for an article, required for a project |
| `cover.png/jpg/gif/webp` | One optional cover; otherwise the built-in illustration is used |
| `images/` | Optional local body images |

Markdown supports headings at levels 1–3, bold, links, local images, fenced code, simple lists, quotations, and pipe tables. Level-one body headings become level two. Raw HTML is escaped; complex nested lists and math are not implemented.

Use `![Screenshot](images/demo.png)` for an image inside the entry folder. Do not use local drive paths or remote image URLs. GIF animation is preserved. PNG, JPG/JPEG, GIF, and WebP are accepted; `.jbg` is only an alias for a mistakenly named JPEG. Keep files UTF-8 and avoid spaces in image filenames. Content hashes prevent stale image caching.

```markdown
| State | Preview |
| :--- | :---: |
| Idle | ![Idle](images/idle.gif) |
```

Tables scroll within their own region on mobile. Pipes inside inline code or escaped as `\|` do not split cells.

## Languages and linked pages

Link `[English](content.en.md)` from content.md, and `[简体中文](content.md)` from the English file. Start the English file with `# English title` to set its detail heading. The generated English URL ends in `/en/`. The app does not translate text or fully localize site navigation.

Link uploaded Markdown with relative paths, such as `[Guide](docs/install.md)`. A directory link such as `[Animations](previews/)` renders that directory's README.md. Images resolve relative to each document; a nested page can link back with `../content.md`. Targets must stay within the entry folder. Missing targets remain plain text; remote repository content is not fetched automatically. Raw Markdown, executable scripts, and configuration are not directly published.

## About page

Initialization also creates `publications/about/`. Edit content.md for the introduction and meta.json for profile fields. Optionally add one avatar.jpg/png/gif/webp file. Body images and tables are supported.

Common fields are name, role, page_title, description, tags, github, gitee, interests, wishes, and quote. Tags and interests are arrays of strings. A wish uses `{"label":"A goal","status":"In progress"}`. Use `\n` for signature line breaks. interests_title, wishlist_title, and eyebrow control section labels.

Empty arrays hide optional lists; links and the quote can be empty strings. Keep only one avatar image. If the entire about directory is absent, a default introduction is used. Invalid existing files stop publication and preserve the live release.

These settings affect the about page; global branding and the homepage remain in site configuration. Real profile data remains Git-ignored with the rest of publications. Use the same publication commands below.

## Publish and unpublish

On Linux:

```bash
python3 blog/publish.py --check
python3 blog/publish.py
```

An isolated build is validated before current is replaced atomically. Failed publication preserves the live release. Folders starting with `_` or `.` and entries marked published=false are excluded. To unpublish, set false and publish again; previous output is not carried into the new release.

Content is published manually. The daily activity job updates only its cached data. Back up content and activity history separately; the source repository deliberately does not contain them.
