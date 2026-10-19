import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build
from library import load_library
import publish


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for kind in ('articles', 'projects'):
            (self.root / kind).mkdir()

    def entry(self, kind='articles', slug='a-post', **meta):
        folder = self.root / kind / slug
        folder.mkdir()
        (folder / 'meta.json').write_text(json.dumps({'title': '真实标题', 'date': '2026-10-19', **meta}), encoding='utf-8')
        (folder / 'summary.md').write_text('## 简介\n\n**重点**与<script>不会执行</script>', encoding='utf-8')
        (folder / 'content.md').write_text('# 正文\n\n## 详细内容\n\n写在这里。', encoding='utf-8')
        (folder / 'link.txt').write_text('https://github.com/WMXhy/My-Blog' if kind == 'projects' else '', encoding='utf-8')
        return folder

    def load(self):
        return load_library(self.root, build.markdown)

    def test_folder_metadata_markdown_and_date_sort(self):
        self.entry(date='2026-10-18')
        self.entry(slug='newer')
        posts, projects, media = self.load()
        self.assertEqual([p['slug'] for p in posts], ['newer', 'a-post'])
        self.assertIn('<strong>重点</strong>', posts[0]['summary_html'])
        self.assertNotIn('id=', posts[0]['summary_html'])
        self.assertIn('&lt;script&gt;', posts[0]['summary_html'])
        self.assertEqual(len(posts[0]['detail'][1]), 2)
        self.assertNotIn('<h1', posts[0]['detail'][0])

    def test_draft_and_template_are_excluded(self):
        draft = self.entry(published=False)
        (draft / 'content.md').unlink()
        (self.root / 'projects/_template').mkdir()
        self.assertEqual(self.load(), ([], [], {}))

    def test_missing_required_files_and_invalid_metadata_fail(self):
        folder = self.entry()
        (folder / 'summary.md').unlink()
        with self.assertRaises(ValueError): self.load()
        (folder / 'summary.md').write_text('简介')
        (folder / 'meta.json').write_text('{"title":"标题","date":"2026-13-99"}')
        with self.assertRaises(ValueError): self.load()

    def test_gif_is_preserved_and_images_are_hashed(self):
        folder = self.entry()
        gif = b'GIF89a-test-image'
        (folder / 'cover.gif').write_bytes(gif)
        (folder / 'content.md').write_text('## 效果\n\n![动画](cover.gif)', encoding='utf-8')
        posts, _, media = self.load()
        self.assertEqual(list(media.values()), [gif])
        self.assertIn(posts[0]['image'], posts[0]['detail'][0])
        old = posts[0]['image']
        (folder / 'cover.gif').write_bytes(gif + b'new')
        self.assertNotEqual(self.load()[0][0]['image'], old)

    def test_jbg_jpeg_alias_and_duplicate_cover(self):
        folder = self.entry()
        (folder / 'cover.jbg').write_bytes(b'\xff\xd8\xff-jpeg')
        self.assertTrue(self.load()[0][0]['image'].endswith('.jpg'))
        (folder / 'cover.png').write_bytes(b'\x89PNG\r\n\x1a\n')
        with self.assertRaisesRegex(ValueError, '只能保留一张'): self.load()

    def test_fake_image_and_path_escape_are_rejected(self):
        folder = self.entry()
        (folder / 'cover.png').write_text('not an image')
        with self.assertRaises(ValueError): self.load()
        (folder / 'cover.png').unlink()
        (self.root / 'outside.png').write_bytes(b'\x89PNG\r\n\x1a\n')
        (folder / 'content.md').write_text('![越界](../../outside.png)')
        with self.assertRaises(ValueError): self.load()
        (folder / 'content.md').write_text('![远程](https://example.com/image.png)')
        with self.assertRaises(ValueError): self.load()

    def test_project_link_required_sorted_and_unsafe_link_rejected(self):
        first = self.entry('projects', order=5)
        self.entry('projects', 'first', order=1)
        self.assertEqual([p['slug'] for p in self.load()[1]], ['first', 'a-post'])
        (first / 'link.txt').write_text('javascript:alert(1)')
        with self.assertRaises(ValueError): self.load()
        (first / 'link.txt').write_text('')
        with self.assertRaises(ValueError): self.load()

    def test_failed_publish_preserves_current_release(self):
        host = self.root / 'blog'
        (host / 'releases/old').mkdir(parents=True)
        (host / 'current').symlink_to('releases/old')
        with patch.object(publish, 'ROOT', host), patch.object(build, 'build', side_effect=ValueError('bad upload')):
            with self.assertRaisesRegex(ValueError, 'bad upload'): publish.publish()
        self.assertEqual((host / 'current').readlink(), Path('releases/old'))

    def test_clean_build_excludes_source_and_generates_project_detail(self):
        self.entry()
        self.entry('projects', 'my-project')
        destination = self.root / 'output'
        with patch.object(build, 'OUT', destination):
            build.build(self.root)
        self.assertTrue((destination / 'posts/a-post/index.html').is_file())
        self.assertTrue((destination / 'projects/my-project/index.html').is_file())
        self.assertFalse(list(destination.rglob('meta.json')))
        self.assertFalse(list(destination.rglob('*.md')))
        self.assertNotIn('/assets/memory.js?', (destination / 'projects/my-project/index.html').read_text())


if __name__ == '__main__':
    unittest.main()
