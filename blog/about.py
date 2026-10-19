"""Read the editable about page from the private sibling content library."""
import json
from pathlib import Path
from library import IMAGE_TYPES, external_url, local_image, read_text


def load_about(library, site, render):
    folder = Path(library) / 'about'
    profile = {
        'name': site['name'], 'role': '大学生 / 代码探索者 / 生活记录者',
        'eyebrow': 'HELLO, NICE TO MEET YOU', 'page_title': '认识一下，小屋的主人',
        'description': '不用很厉害才开始。把每一次探索，都认真地放进自己的小小世界。',
        'tags': ['保持好奇', '慢慢生长'], 'github': site['github'], 'gitee': site['gitee'],
        'interests_title': '这个小屋，关心这些小事',
        'interests': ['编程与项目', '学习笔记', '日常碎片', '可爱的交互'],
        'wishlist_title': '还想慢慢完成的事',
        'wishes': [{'label': 'GitHub / Gitee 代码小花园', 'status': '已上线'},
                   {'label': '花朵翻翻乐，随手玩一小会儿', 'status': '已上线'},
                   {'label': '持续写文章，为作品补上更多故事', 'status': '慢慢积累'}],
        'quote': '今天也在慢慢生长。\n愿我们都能做一点自己喜欢的事。',
    }
    content = ('欢迎来到我的个人小屋。我是一名大学生，希望用这个空间，把学习、项目和生活中想留下的片刻慢慢整理起来。\n\n'
               '这里有我的学习笔记，也有放在 GitHub 和 Gitee 上的代码。小屋会随着新的想法一点点变化，认真记录，也给有趣的事情留一点位置。')
    media = {}
    if folder.exists():
        config = json.loads(read_text(folder, 'meta.json'))
        if not isinstance(config, dict):
            raise ValueError(f'{folder}: meta.json 必须是 JSON 对象')
        unknown = set(config) - set(profile)
        if unknown:
            raise ValueError(f'{folder}: meta.json 中未识别的字段：{", ".join(sorted(unknown))}')
        profile.update(config)
        content = read_text(folder, 'content.md')
    for key in ('name', 'role', 'eyebrow', 'page_title', 'description', 'github', 'gitee', 'interests_title', 'wishlist_title', 'quote'):
        if not isinstance(profile[key], str):
            raise ValueError(f'{folder}: {key} 应为文字')
    if not profile['name'].strip() or not profile['page_title'].strip():
        raise ValueError(f'{folder}: name 和 page_title 不能为空')
    for key in ('tags', 'interests'):
        if not isinstance(profile[key], list) or not all(isinstance(value, str) for value in profile[key]):
            raise ValueError(f'{folder}: {key} 应为文字数组')
    if not isinstance(profile['wishes'], list) or not all(
            isinstance(wish, dict) and isinstance(wish.get('label'), str) and isinstance(wish.get('status'), str)
            for wish in profile['wishes']):
        raise ValueError(f'{folder}: wishes 应为包含 label 和 status 文字的数组')
    for key in ('github', 'gitee'):
        if profile[key]:
            try:
                external_url(profile[key], folder)
            except ValueError:
                raise ValueError(f'{folder}: {key} 需要完整的 http:// 或 https:// 地址，也可留空') from None
    profile['image'] = None
    if folder.exists():
        avatars = [p for p in folder.iterdir() if p.is_file() and p.stem.lower() == 'avatar' and p.suffix.lower() in IMAGE_TYPES]
        if len(avatars) > 1:
            raise ValueError(f'{folder}: avatar 头像只能保留一张')
        if avatars:
            profile['image'] = local_image(folder, avatars[0].name, Path('about'), media)
    profile['html'] = render(content, lambda reference: local_image(folder, reference, Path('about'), media))[0]
    return profile, media
