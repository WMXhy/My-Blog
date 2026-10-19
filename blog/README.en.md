# Application source

[简体中文](README.md) · **English**

Start with the [repository README](../README.en.md).

- `build.py`: static page generation.
- `library.py`: folder-managed entries and linked Markdown pages.
- `init_content.py`: create the ignored publications library at the repository root.
- `publish.py`: validate and publish atomically on Linux.
- `validate.py`: metadata, local links, anchors, and image checks.
- `assets/`: shared appearance, themes, activity UI, and the memory game.
- `activity/`: public calendars and Push collection; see [activity notes](../docs/ACTIVITY.en.md).
- `deploy/`: configurable systemd and Nginx examples; see [deployment](../docs/DEPLOYMENT.en.md).

Real editorial content belongs in the sibling publications directory and is excluded from Git. See the [content guide](../docs/CONTENT.en.md).
