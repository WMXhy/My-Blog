import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build
from about import load_about


class AboutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.library = Path(self.temp.name)

    def write(self, config):
        folder = self.library / 'about'
        folder.mkdir(exist_ok=True)
        (folder / 'meta.json').write_text(json.dumps(config, ensure_ascii=False), encoding='utf-8')
        (folder / 'content.md').write_text('## 新的一页\n\n这是 **修改后的介绍**。', encoding='utf-8')
        return folder

    def load(self):
        return load_about(self.library, build.SITE, build.markdown)

    def test_missing_directory_preserves_default_page(self):
        profile, media = self.load()
        self.assertEqual(profile['name'], build.SITE['name'])
        self.assertIn('欢迎来到我的个人小屋', profile['html'])
        self.assertFalse(media)

    def test_external_content_and_profile_are_used_and_escaped(self):
        self.write({'name': '<script>昵称</script>', 'role': '新的身份', 'interests': ['摄影'],
                    'wishes': [{'label': '写新文章', 'status': '进行中'}], 'quote': '第一句\n第二句'})
        profile, _ = self.load()
        body = build.about_body(profile)
        self.assertIn('<strong>修改后的介绍</strong>', body)
        self.assertIn('新的身份', body)
        self.assertIn('摄影', body)
        self.assertIn('第一句<br>第二句', body)
        self.assertIn('&lt;script&gt;昵称&lt;/script&gt;', body)
        self.assertNotIn('<script>', body)

    def test_avatar_and_body_images_use_private_folder_media(self):
        folder = self.write({})
        data = b'\x89PNG\r\n\x1a\n-test'
        (folder / 'avatar.png').write_bytes(data)
        (folder / 'content.md').write_text('![头像](avatar.png)', encoding='utf-8')
        profile, media = self.load()
        self.assertTrue(profile['image'].startswith('/media/about/avatar-'))
        self.assertIn(profile['image'], profile['html'])
        self.assertEqual(list(media.values()), [data])

    def test_invalid_config_and_missing_content_fail(self):
        for config in ({'interests': 'not a list'}, {'wishes': ['bad']}, {'name': ''},
                       {'github': 'javascript:alert(1)'}, {'page_titel': 'typo'}):
            self.write(config)
            with self.assertRaises(ValueError): self.load()
        folder = self.write({})
        (folder / 'content.md').unlink()
        with self.assertRaises(ValueError): self.load()

    def test_duplicate_avatar_and_outside_images_fail(self):
        folder = self.write({})
        (folder / 'avatar.png').write_bytes(b'\x89PNG\r\n\x1a\n')
        (folder / 'avatar.gif').write_bytes(b'GIF89a-test')
        with self.assertRaises(ValueError): self.load()
        (folder / 'avatar.gif').unlink()
        (self.library / 'outside.png').write_bytes(b'\x89PNG\r\n\x1a\n')
        (folder / 'content.md').write_text('![越界](../outside.png)', encoding='utf-8')
        with self.assertRaises(ValueError): self.load()

    def test_optional_sections_can_be_removed(self):
        self.write({'tags': [], 'interests': [], 'wishes': [], 'quote': '', 'github': '', 'gitee': ''})
        profile, _ = self.load()
        body = build.about_body(profile)
        self.assertNotIn('class="interest-list"', body)
        self.assertNotIn('class="wish-list"', body)
        self.assertNotIn('class="about-quote"', body)


if __name__ == '__main__':
    unittest.main()
