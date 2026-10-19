"""Load author-managed article/project folders, without publishing source files."""
import hashlib
from html.parser import HTMLParser
import json
from datetime import date
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit

IMAGE_TYPES = {'.png', '.jpg', '.jpeg', '.jbg', '.gif', '.webp'}
ART_TYPES = {'house', 'code', 'garden', 'pet'}


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            self.parts.append(dict(attrs).get('alt', ''))


def plain_text(markup):
    parser = PlainText()
    parser.feed(markup)
    return ' '.join(' '.join(parser.parts).split())


def safe_file(folder, name):
    path = (folder / name).resolve()
    if not path.is_relative_to(folder.resolve()) or not path.is_file():
        raise ValueError(f'{folder}: 文件不存在或超出当前文件夹：{name}')
    return path


def read_text(folder, name, required=True):
    if not (folder / name).exists() and not required:
        return ''
    content = safe_file(folder, name).read_text(encoding='utf-8-sig').strip()
    if required and not content:
        raise ValueError(f'{folder}: {name} 不能为空')
    return content


def external_url(value, folder):
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password or any(c.isspace() for c in value):
        raise ValueError(f'{folder}: link.txt 需要完整的 http:// 或 https:// 链接，一行一个网址，只填写一个')
    return value


def local_image(folder, reference, namespace, media):
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or parsed.path.startswith(('/', '\\')):
        raise ValueError(f'{folder}: 图片请使用当前文件夹内的相对路径：{reference}')
    file = safe_file(folder, unquote(parsed.path))
    suffix = file.suffix.lower()
    if suffix not in IMAGE_TYPES:
        raise ValueError(f'{file}: 图片支持 png/jpg/jpeg/gif/webp，误写为 jbg 的 JPEG 也可识别')
    data = file.read_bytes()
    valid = (suffix == '.png' and data.startswith(b'\x89PNG\r\n\x1a\n')
             or suffix in ('.jpg', '.jpeg', '.jbg') and data.startswith(b'\xff\xd8\xff')
             or suffix == '.gif' and data[:6] in (b'GIF87a', b'GIF89a')
             or suffix == '.webp' and data.startswith(b'RIFF') and data[8:12] == b'WEBP')
    if not valid:
        raise ValueError(f'{file}: 图片内容与扩展名不符，请放入真实图片')
    relative = file.relative_to(folder.resolve())
    extension = '.jpg' if suffix == '.jbg' else suffix
    output = Path('media') / namespace / relative.parent / f'{relative.stem}-{hashlib.sha256(data).hexdigest()[:12]}{extension}'
    media[output] = data
    return '/' + quote(output.as_posix(), safe='/')


def load_library(root, render):
    root = Path(root)
    media, entries = {}, {'articles': [], 'projects': []}
    for kind in entries:
        parent = root / kind
        if not parent.is_dir():
            raise ValueError(f'内容目录不存在：{parent}')
        for folder in sorted(parent.iterdir()):
            if not folder.is_dir() or folder.name.startswith(('.', '_')):
                continue
            if folder.is_symlink() or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', folder.name):
                raise ValueError(f'{folder}: 文件夹名称请使用小写英文、数字与短横线，例如 my-first-post')
            meta = json.loads(read_text(folder, 'meta.json'))
            if not isinstance(meta, dict) or type(meta.get('published', True)) is not bool:
                raise ValueError(f'{folder}: meta.json 必须是对象，published 只能填写 true 或 false')
            if not meta.get('published', True):
                continue
            title = meta.get('title')
            if not isinstance(title, str) or not title.strip():
                raise ValueError(f'{folder}: meta.json 缺少 title 标题')
            date.fromisoformat(meta['date'])
            tags = meta.get('tags', [])
            if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                raise ValueError(f'{folder}: tags 应为字符串数组')
            art = meta.get('art', 'garden' if kind == 'articles' else 'code')
            if art not in ART_TYPES:
                raise ValueError(f'{folder}: art 只能是 house/code/garden/pet')
            category = meta.get('category', '学习笔记')
            subtitle = meta.get('subtitle', '')
            image_fit = meta.get('image_fit', 'cover')
            order = meta.get('order', 100)
            if not isinstance(category, str) or not isinstance(subtitle, str) or image_fit not in ('cover', 'contain') or type(order) is not int:
                raise ValueError(f'{folder}: category/subtitle 应为文字，image_fit 为 cover/contain，order 为整数')
            link = read_text(folder, 'link.txt', required=(kind == 'projects'))
            public_link = external_url(link, folder) if link else ''
            base = f'/{"posts" if kind == "articles" else "projects"}/{folder.name}/'
            pending = ['content.md']
            documents = {}
            for translation in sorted(folder.glob('content.*.md')):
                if re.fullmatch(r'content\.[a-z]{2,3}(?:-[A-Za-z]{2,4})?\.md', translation.name):
                    pending.append(translation.name)

            def document_path(relative):
                if relative == 'content.md':
                    return base
                language = re.fullmatch(r'content\.([a-z]{2,3}(?:-[A-Za-z]{2,4})?)\.md', relative)
                if language:
                    return base + language[1] + '/'
                return base + 'read/' + quote(Path(relative).with_suffix('').as_posix(), safe='/') + '/'

            def image_url(reference, folder=folder, kind=kind):
                return local_image(folder, reference, Path(kind) / folder.name, media)

            covers = [file for file in folder.iterdir() if file.is_file() and file.stem.lower() == 'cover' and file.suffix.lower() in IMAGE_TYPES]
            if len(covers) > 1:
                raise ValueError(f'{folder}: cover 图片只能保留一张，删除旧封面后再发布')
            image = image_url(covers[0].name) if covers else None
            summary = read_text(folder, 'summary.md')
            # A short introduction is reused in several places, so it has no heading IDs.
            summary = re.sub(r'(?m)^#{1,6}\s+', '', summary)
            summary_html = render(summary, image_url)[0]
            description = plain_text(summary_html)
            if not description:
                raise ValueError(f'{folder}: summary.md 需要文字短介绍')
            while pending:
                relative = pending.pop(0)
                if relative in documents:
                    continue
                if len(documents) >= 64:
                    raise ValueError(f'{folder}: 引用的 Markdown 页面过多（最多 64 页）')
                source = read_text(folder, relative)

                def resolve_image(reference, relative=relative):
                    return image_url((Path(relative).parent / unquote(reference)).as_posix())

                def resolve_link(reference, relative=relative):
                    parsed = urlsplit(reference)
                    if parsed.scheme or parsed.netloc:
                        return None
                    candidate = (folder / Path(relative).parent / unquote(parsed.path)).resolve()
                    if not candidate.is_relative_to(folder.resolve()):
                        raise ValueError(f'{folder}: 链接不能超出当前内容文件夹：{reference}')
                    if candidate.is_dir() and (candidate / 'README.md').is_file():
                        candidate /= 'README.md'
                    if not candidate.is_file():
                        return None
                    target = candidate.relative_to(folder.resolve()).as_posix()
                    if candidate.suffix.lower() == '.md':
                        if target not in documents:
                            pending.append(target)
                        return document_path(target) + (f'#{parsed.fragment}' if parsed.fragment else '')
                    if candidate.suffix.lower() in IMAGE_TYPES:
                        return image_url(target)
                    # Executables, configuration and arbitrary source files stay private.
                    return None

                language = re.fullmatch(r'content\.([a-z]{2,3}(?:-[A-Za-z]{2,4})?)\.md', relative)
                language = language[1] if language else 'zh-CN'
                heading = re.search(r'^#\s+(.+)', source, re.M)
                doc_title = heading[1].strip() if heading and relative != 'content.md' else title.strip()
                documents[relative] = {'path': document_path(relative), 'language': language,
                                       'primary': relative == 'content.md',
                                       'title': doc_title, 'detail': render(source, resolve_image, resolve_link)}
            item = {'slug': folder.name, 'title': title.strip(), 'name': title.strip(), 'date': meta['date'],
                    'description': description, 'summary_html': summary_html, 'detail': documents['content.md']['detail'],
                    'category': category, 'tags': tags, 'art': art, 'image': image,
                    'image_fit': image_fit, 'subtitle': subtitle, 'order': order,
                    'url': public_link, 'documents': list(documents.values())}
            entries[kind].append(item)
    entries['articles'].sort(key=lambda item: item['date'], reverse=True)
    entries['projects'].sort(key=lambda item: item['order'])
    return entries['articles'], entries['projects'], media
