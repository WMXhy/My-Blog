#!/usr/bin/env python3
"""Validate built routes, local links, anchors, and metadata without dependencies."""
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

DIST = Path(__file__).resolve().parent / 'dist'


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.h1 = set(), [], 0
        self.lang = self.title = self.viewport = self.canonical = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            if attrs['id'] in self.ids:
                raise ValueError('Duplicate element ID: ' + attrs['id'])
            self.ids.add(attrs['id'])
        self.h1 += tag == 'h1'
        self.lang |= tag == 'html' and attrs.get('lang') == 'zh-CN'
        self.title |= tag == 'title'
        self.viewport |= tag == 'meta' and attrs.get('name') == 'viewport'
        self.canonical |= tag == 'link' and attrs.get('rel') == 'canonical'
        if tag in ('a', 'link', 'use') and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag == 'script' and attrs.get('src'):
            self.links.append(attrs['src'])
        if tag == 'img' and attrs.get('src'):
            self.links.append(attrs['src'])
        if tag == 'a' and attrs.get('target') == '_blank':
            assert 'noopener' in attrs.get('rel', ''), 'External link needs noopener'


def main():
    pages = {}
    for file in DIST.rglob('*.html'):
        parser = Page()
        parser.feed(file.read_text(encoding='utf-8'))
        assert parser.h1 == 1, f'{file}: expected exactly one h1'
        assert all((parser.lang, parser.title, parser.viewport, parser.canonical)), f'{file}: missing metadata'
        pages[file.resolve()] = parser
    assert len(pages) >= 7, 'Missing expected pages'
    assert (DIST / 'play/index.html').is_file() and (DIST / 'friends/index.html').is_file()
    for file in DIST.rglob('*.html'):
        source = file.read_text(encoding='utf-8')
        assert ('/assets/memory.js?' in source) == (file == DIST / 'play/index.html'), f'{file}: game loaded outside playground'
        assert '每天凌晨 04:00' in source if file == DIST / 'index.html' else True
    checks = 0
    for file, parser in pages.items():
        for link in parser.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                continue
            target = DIST / unquote(parsed.path).lstrip('/') if parsed.path.startswith('/') else file.parent / unquote(parsed.path) if parsed.path else file
            if target.is_dir():
                target /= 'index.html'
            assert target.is_file(), f'{file}: broken local link {link}'
            if parsed.fragment and target.suffix == '.html':
                assert unquote(parsed.fragment) in pages[target.resolve()].ids, f'{file}: missing anchor {link}'
            if parsed.fragment and target.suffix == '.svg':
                root = ElementTree.parse(target)
                assert any(node.get('id') == parsed.fragment for node in root.iter()), f'Missing illustration {link}'
            checks += 1
    for name in ('feed.xml', 'sitemap.xml', 'assets/illustrations.svg', 'assets/favicon.svg'):
        ElementTree.parse(DIST / name)
    print(f'PASS: {len(pages)} pages; {checks} local links/assets/anchors; XML; metadata; external-link safety.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'FAIL: {error}', file=sys.stderr)
        sys.exit(1)
