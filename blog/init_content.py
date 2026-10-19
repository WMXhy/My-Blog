#!/usr/bin/env python3
"""Initialize an ignored content library without overwriting existing files."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent


def initialize():
    library = ROOT.parent / 'publications'
    examples = ROOT.parent / 'examples'
    if not examples.is_dir():
        raise SystemExit('Missing examples directory. Run this script from a complete repository checkout.')
    for relative, template in [('articles/_template', 'article'), ('projects/_template', 'project'), ('about', 'about')]:
        destination = library / relative
        destination.mkdir(parents=True, exist_ok=True)
        for source in (examples / template).iterdir():
            target = destination / source.name
            if source.is_file() and not target.exists():
                shutil.copy2(source, target)
    guide = library / 'README.md'
    if not guide.exists():
        guide.write_text('Content stays local and is ignored by Git.\n\nSee ../docs/CONTENT.zh-CN.md or ../docs/CONTENT.en.md for the folder format and publishing commands.\n', encoding='utf-8')
    print(f'Content library ready: {library}. Existing files were preserved.')


if __name__ == '__main__':
    initialize()
