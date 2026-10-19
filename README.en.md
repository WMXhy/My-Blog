# My-Blog · A Little Growing Space

[简体中文](README.md) · **English**

Cream, sage green, and a little dusty rose. This repository contains the source of XingKuiJueLong's personal blog: a place for learning notes, small projects, and a quiet break.

[Visit the site](https://xingkuijuelong.cn/) · [Project story](https://xingkuijuelong.cn/projects/my-blog/en/) · [Deployment](docs/DEPLOYMENT.en.md) · [Content format](docs/CONTENT.en.md)

## Inside the house

- **Notebook:** Markdown articles, categories, search, reading outlines, RSS, sitemap, and a custom 404 page.
- **Project drawer:** cards, dedicated detail pages, cover images and GIFs, and external project links.
- **Code garden:** public GitHub / Gitee contribution calendars with Total / GitHub / Gitee selection; public Push events are counted separately.
- **Flower memory:** a 16-card matching game with elapsed time, a browser-local personal best, and background-tab pause.
- **Gentle themes:** cream, night green, and system preference, remembered by the browser.
- **Neighbourhood:** friend links and a copyable site introduction.
- **Mobile reading:** calendars and tables scroll within their own regions; reduced-motion preferences are respected.

The Markdown renderer supports local images, animated GIFs, tables, code fences, simple lists, and quotations. Link `content.md` and `content.en.md` to publish bilingual detail pages. Site navigation is primarily Chinese; language pages use author-supplied text and do not provide automatic translation.

## A small stack

| Part | Implementation |
| --- | --- |
| Static generation | Python 3.12+ standard library, no third-party Python packages |
| Browser interactions | Vanilla JavaScript and CSS, local fonts and assets |
| Web server | Nginx static hosting; no persistent Python or Node application server |
| Activity collection | Python, SQLite, and a systemd timer at 04:00 Asia/Shanghai daily |
| Publishing | Isolated build, link validation, atomic release symlink replacement |

Calendar data comes from public platform pages; Push history comes from public event APIs. No account token is required. Contributions and Push counts are different measurements. Total adds the two platform counts, so mirrored work may count on both. Event history is bounded and upstream markup may change. Failed syncs retain previous successful data, and unknown dates are not represented as zero. See [activity notes](docs/ACTIVITY.en.md).

## Preview locally

With Python 3.12 or newer, run from the repository root:

```bash
python3 blog/init_content.py
python3 blog/build.py
python3 blog/validate.py
python3 -m http.server 8000 --directory blog/dist
```

Open [the preview](http://localhost:8000). Initialization creates the Git-ignored `publications/` library and draft templates, preserves existing files, and does not include the author's articles or projects.

A plain static preview does not provide `/api/activity`, so the garden will show an unavailable state. Configure the cache endpoint and sync service using the deployment guide to display real data. Publishing and synchronization use Linux file locks; run those tools on a Linux host.

## Add content

```text
My-Blog/
├── blog/                         Application source
├── docs/                         Bilingual maintenance guides
├── examples/                     Generic draft templates
└── publications/                 Created locally; ignored by Git
    ├── articles/my-first-post/   One folder per article
    └── projects/my-project/      One folder per project
```

Each entry contains `meta.json`, an optional `cover.png/jpg/gif`, `link.txt`, `summary.md`, and `content.md`. Add `content.en.md` for English text. Copy a template, rename the folder, edit the files, and set `published` to `true`. On the server:

```bash
python3 blog/publish.py --check  # Validate only
python3 blog/publish.py          # Validate and publish
```

A failed build leaves the live release intact. To unpublish an entry, set `published` to `false` and publish again. Uploading files does not immediately publish them, and the daily activity sync does not publish editorial content.

## Configuration and checks

- `blog/site.json`: site identity, URL, profiles, and friend links.
- `blog/activity/config.json`: public accounts and repositories included in Push collection.
- `blog/build.py`: layout and site-specific footer; replace identity and registration information before reuse.
- `blog/deploy/`: Nginx example and systemd unit files.

```bash
python3 -m unittest discover -s blog/tests -p 'test_*.py' -v
(cd blog/activity && python3 -m unittest -v test_sync)
node blog/tests/memory.test.cjs
```

Node.js is used only for game logic verification; hosting the site does not require it. GitHub Actions runs these checks and an empty-library build. Live upstream synchronization runs on the server, not in CI.

## Repository boundaries

This repository contains source, required static assets, generic templates, tests, and documentation. It excludes the author's `publications/`, SQLite history, HTTP caches, build output, server credentials, and actual TLS configuration. The original [Chinese project plan](个人博客建设方案.md) is retained as background; use this README and docs for current operation.

Comments, accounts, and online leaderboards are not implemented. Game records and theme choices stay in the current browser.
