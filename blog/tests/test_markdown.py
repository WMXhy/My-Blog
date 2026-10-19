from pathlib import Path
import sys
import tempfile
import unittest
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build
from library import load_library


class MarkdownTests(unittest.TestCase):
    def test_table_images_and_center_alignment(self):
        source = '| 待机 | 挥手 | 跳跃 |\n| :---: | :---: | :---: |\n| ![待机](idle.gif) | ![挥手](wave.gif) | ![跳跃](jump.gif) |'
        markup, _ = build.markdown(source, lambda path: '/media/' + path)
        self.assertEqual(markup.count('<table>'), 1)
        self.assertEqual(markup.count('<th scope='), 3)
        self.assertEqual(markup.count('<td class='), 3)
        self.assertEqual(markup.count('<img '), 3)
        self.assertIn('markdown-table-scroll', markup)
        self.assertIn('class="align-center"', markup)
        self.assertNotIn(':---:', markup)

    def test_code_and_escaped_pipes_do_not_split_cells(self):
        source = '| 文件 | 用途 |\n| --- | --- |\n| `a|b.txt` | 含有 \\| 的说明 |'
        markup, _ = build.markdown(source)
        self.assertEqual(markup.count('<td class='), 2)
        self.assertIn('<code>a|b.txt</code>', markup)
        self.assertIn('含有 | 的说明', markup)

    def test_tables_in_code_blocks_remain_code_and_html_is_escaped(self):
        markup, _ = build.markdown('```\n| a | b |\n| --- | --- |\n```\n\n| a | b |\n| --- | --- |\n| <script>alert(1)</script> | ok |')
        self.assertEqual(markup.count('<table>'), 1)
        self.assertIn('&lt;script&gt;', markup)
        self.assertNotIn('<script>', markup)

    def test_language_links_and_nested_markdown_images(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'articles').mkdir()
            folder = root / 'projects/pet'
            folder.mkdir(parents=True)
            (folder / 'meta.json').write_text(json.dumps({'title': '桌宠', 'date': '2026-10-19'}))
            (folder / 'summary.md').write_text('短介绍')
            (folder / 'link.txt').write_text('https://github.com/WMXhy/My-Blog')
            (folder / 'content.md').write_text('[English](content.en.md) · **简体中文**\n\n[动画](previews/)')
            (folder / 'content.en.md').write_text('# English title\n\n**English** · [简体中文](content.md)')
            (folder / 'previews').mkdir()
            (folder / 'previews/README.md').write_text('# 动画\n\n![挥手](wave.gif)\n\n[返回](../content.md)')
            (folder / 'previews/wave.gif').write_bytes(b'GIF89a-animation')
            _, projects, media = load_library(root, build.markdown)
            docs = {doc['path']: doc for doc in projects[0]['documents']}
            self.assertEqual(len(docs), 3)
            self.assertIn('href="/projects/pet/en/"', docs['/projects/pet/']['detail'][0])
            self.assertIn('href="/projects/pet/"', docs['/projects/pet/en/']['detail'][0])
            self.assertEqual(docs['/projects/pet/en/']['language'], 'en')
            self.assertEqual(docs['/projects/pet/en/']['title'], 'English title')
            self.assertIn('/projects/pet/read/previews/README/', docs['/projects/pet/']['detail'][0])
            self.assertIn('/media/projects/pet/previews/wave-', docs['/projects/pet/read/previews/README/']['detail'][0])
            self.assertEqual(len(media), 1)

    def test_unsafe_relative_link_is_not_followed(self):
        markup, _ = build.markdown('[bad](javascript:alert(1))')
        self.assertNotIn('<a ', markup)


if __name__ == '__main__':
    unittest.main()
