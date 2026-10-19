#!/usr/bin/env python3
"""Build a small, dependency-free static blog from Markdown and JSON."""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from library import load_library
from about import load_about
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "dist"
SITE = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
POSTS = []
PROJECTS = []
VERSION = hashlib.sha256(b"".join(p.read_bytes() for p in sorted((ROOT / "assets").glob("*")))).hexdigest()[:12]


def e(value):
    return html.escape(str(value), quote=True)


def art(name, css="", label=None):
    attrs = f'role="img" aria-label="{e(label)}"' if label else 'aria-hidden="true"'
    return f'<svg class="{e(css)}" viewBox="0 0 {"48 48" if name == "sprout" else "600 470"}" {attrs}><use href="/assets/illustrations.svg?v={VERSION}#{e(name)}"></use></svg>'


def external(url, title, css=""):
    return f'<a class="{e(css)}" href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(title)} <span aria-hidden="true">↗</span><span class="sr-only">（新窗口）</span></a>'


def socials():
    return '<div class="social-row">' + external(SITE["github"], "GitHub") + external(SITE["gitee"], "Gitee") + '</div>'


def avatar():
    return f'<img class="profile-avatar" src="/assets/avatar.jpg?v={VERSION}" width="1080" height="1080" alt="{e(SITE["name"])} 的头像" loading="lazy" decoding="async">'


def inline(value, image_resolver=None, link_resolver=None):
    # Escape all author HTML, then render only a deliberately small inline subset.
    escaped = e(value)
    tokens = []

    def save_code(match):
        tokens.append(f'<code>{match.group(1)}</code>')
        return f'\x00{len(tokens) - 1}\x00'

    escaped = re.sub(r'`([^`]+)`', save_code, escaped)
    def image(match):
        if image_resolver is None:
            return match.group(1)
        url = image_resolver(html.unescape(match.group(2)))
        tokens.append(f'<img class="prose-image" src="{e(url)}" alt="{match.group(1)}" loading="lazy" decoding="async">')
        return f'\x00{len(tokens) - 1}\x00'
    escaped = re.sub(r'!\[([^\]]*)\]\(([^\s)]+)\)', image, escaped)
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)

    def link(match):
        title, url = match.group(1), html.unescape(match.group(2))
        if link_resolver and not url.startswith(('https://', 'http://', '/', '#')):
            url = link_resolver(url) or ''
        if not (url.startswith(("https://", "http://", '#')) or (url.startswith("/") and not url.startswith("//"))):
            return title
        attrs = ' target="_blank" rel="noopener noreferrer"' if url.startswith(("http://", "https://")) else ''
        return f'<a href="{e(url)}"{attrs}>{title}</a>'

    escaped = re.sub(r'\[([^\]]+)\]\(([^\s)]+)\)', link, escaped)
    return re.sub(r'\x00(\d+)\x00', lambda m: tokens[int(m.group(1))], escaped)


def table_cells(line):
    """Split table delimiters while preserving escaped pipes and inline code."""
    line = line.strip()
    cells, cell, ticks = [], [], 0
    index = 0
    while index < len(line):
        char = line[index]
        if char == '\\' and index + 1 < len(line) and line[index + 1] == '|':
            cell.append('|')
            index += 2
            continue
        if char == '`':
            end = index + 1
            while end < len(line) and line[end] == '`':
                end += 1
            run = end - index
            ticks = run if not ticks else 0 if ticks == run else ticks
            cell.append(line[index:end])
            index = end
            continue
        if char == '|' and not ticks:
            cells.append(''.join(cell).strip())
            cell = []
        else:
            cell.append(char)
        index += 1
    cells.append(''.join(cell).strip())
    if line.startswith('|'):
        cells.pop(0)
    if line.endswith('|') and cells and not cells[-1]:
        cells.pop()
    return cells


def markdown(source, image_resolver=None, link_resolver=None):
    output, toc, paragraph, code = [], [], [], []
    list_type = None
    in_code = False

    def flush():
        if paragraph:
            output.append('<p>' + inline(' '.join(paragraph), image_resolver, link_resolver) + '</p>')
            paragraph.clear()

    def close_list():
        nonlocal list_type
        if list_type:
            output.append(f'</{list_type}>')
            list_type = None

    lines = source.splitlines()
    position = 0
    while position < len(lines):
        line = lines[position]
        position += 1
        if line.startswith('```'):
            flush()
            close_list()
            if in_code:
                output.append('<pre><code>' + e('\n'.join(code)) + '</code></pre>')
                code.clear()
            in_code = not in_code
            continue
        if in_code:
            code.append(line)
            continue
        if not line.strip():
            flush()
            close_list()
            continue
        if '|' in line and position < len(lines):
            headers = table_cells(line)
            separators = table_cells(lines[position])
            if headers and len(headers) == len(separators) and all(re.fullmatch(r':?-{3,}:?', value) for value in separators):
                flush()
                close_list()
                position += 1
                alignments = ['center' if value.startswith(':') and value.endswith(':') else 'right' if value.endswith(':') else 'left' for value in separators]
                output.append('<div class="markdown-table-scroll" role="region" aria-label="文中表格" tabindex="0"><table><thead><tr>')
                for value, align in zip(headers, alignments):
                    output.append(f'<th scope="col" class="align-{align}">{inline(value, image_resolver, link_resolver)}</th>')
                output.append('</tr></thead><tbody>')
                while position < len(lines) and lines[position].strip() and '|' in lines[position]:
                    cells = table_cells(lines[position])
                    position += 1
                    cells = (cells + [''] * len(headers))[:len(headers)]
                    output.append('<tr>')
                    for value, align in zip(cells, alignments):
                        output.append(f'<td class="align-{align}">{inline(value, image_resolver, link_resolver)}</td>')
                    output.append('</tr>')
                output.append('</tbody></table></div>')
                continue
        heading = re.match(r'^(#{1,3})\s+(.+)$', line)
        if heading:
            flush()
            close_list()
            level, title = max(2, len(heading[1])), heading[2]
            anchor = f'section-{len(toc) + 1}'
            toc.append((anchor, title))
            output.append(f'<h{level} id="{anchor}">{inline(title, image_resolver, link_resolver)}</h{level}>')
            continue
        if line.startswith('> '):
            flush()
            close_list()
            output.append('<blockquote><p>' + inline(line[2:], image_resolver, link_resolver) + '</p></blockquote>')
            continue
        item = re.match(r'^(?:([-*])|\d+\.)\s+(.+)$', line)
        if item:
            flush()
            kind = 'ul' if item[1] else 'ol'
            if list_type != kind:
                close_list()
                output.append(f'<{kind}>')
                list_type = kind
            output.append('<li>' + inline(item[2], image_resolver, link_resolver) + '</li>')
            continue
        close_list()
        paragraph.append(line)
    flush()
    close_list()
    if in_code:
        raise ValueError('Unclosed Markdown code fence')
    return '\n'.join(output), toc


def page(path, title, body, active="", description=None, noindex=False):
    canonical = SITE["url"].rstrip('/') + path
    activity_assets = f'<link rel="stylesheet" href="/assets/activity.css?v={VERSION}"><script src="/assets/activity.js?v={VERSION}" defer></script>' if active == 'home' else ''
    play_assets = f'<link rel="stylesheet" href="/assets/play.css?v={VERSION}"><script src="/assets/memory.js?v={VERSION}" defer></script>' if active == 'play' else ''
    nav = ''.join(f'<a href="{url}"' + (' aria-current="page"' if active == key else '') + f'>{label}</a>' for key, url, label in [('home', '/', '首页'), ('articles', '/articles/', '文章'), ('projects', '/projects/', '项目'), ('play', '/play/', '游乐角'), ('friends', '/friends/', '友链'), ('about', '/about/', '关于我')])
    document = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · {e(SITE['title'])}</title>
<meta name="description" content="{e(description or SITE['description'])}">
<meta name="theme-color" content="#faf8f2">
<script src="/assets/theme.js?v={VERSION}"></script>
<meta property="og:type" content="{'article' if path.startswith('/posts/') else 'website'}"><meta property="og:title" content="{e(title)} · {e(SITE['title'])}"><meta property="og:description" content="{e(description or SITE['description'])}"><meta property="og:url" content="{e(canonical)}"><meta property="og:locale" content="zh_CN">
{'<meta name="robots" content="noindex">' if noindex else ''}
<link rel="canonical" href="{e(canonical)}"><link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
<link rel="alternate" type="application/rss+xml" title="小屋的更新" href="/feed.xml">
<link rel="stylesheet" href="/assets/site.css?v={VERSION}"><script src="/assets/site.js?v={VERSION}" defer></script>
{activity_assets}
{play_assets}
</head>
<body id="top">
<a class="skip" href="#main">跳到正文</a>
<header class="site-header"><div class="wrap header-inner">
<a class="brand" href="/" aria-label="{e(SITE['name'])} 的小屋，返回首页"><span class="brand-icon">{art('sprout')}</span><span><span class="brand-name">{e(SITE['name'])}</span><small>A LITTLE GROWING SPACE</small></span></a>
<div class="header-actions"><button class="theme-toggle" data-theme-toggle type="button" hidden aria-label="切换配色">☾</button><button class="menu-button" data-menu aria-controls="main-nav" aria-expanded="false" hidden>菜单 ☰</button></div>
<nav class="nav" id="main-nav" aria-label="主导航">{nav}{external(SITE['github'], 'GitHub', 'external')}</nav>
</div></header>
<main id="main" class="wrap">{body}</main>
<div class="wrap theme-preference" hidden><label for="theme-choice">小屋配色</label><select id="theme-choice" data-theme-choice><option value="light">奶油白</option><option value="dark">静夜绿</option><option value="system">跟随系统</option></select><span data-theme-status role="status"></span></div><footer class="site-footer"><div class="wrap footer-inner"><div><p>© {date.today().year} {e(SITE['name'])} · 把日子写成喜欢的样子</p><p>在自己的小小宇宙里，慢慢生长。<span aria-hidden="true"> ✿</span></p></div><div class="footer-links">{external(SITE['github'], 'GitHub')}{external(SITE['gitee'], 'Gitee')}<a href="/feed.xml">RSS 订阅</a><a href="#top">回到顶部 ↑</a></div></div><div class="wrap footer-registration" aria-label="网站备案信息"><a href="https://beian.miit.gov.cn" target="_blank" rel="noopener noreferrer">赣ICP备2026022906号-1</a><a href="https://www.beian.gov.cn" target="_blank" rel="noopener noreferrer"><img src="/assets/beian-police.png" width="20" height="22" alt="" loading="lazy" decoding="async"><span>赣公网安备36073202360966号</span></a></div></footer>

</body></html>'''
    target = OUT / ('404.html' if path == '/404.html' else unquote(path.strip('/')) + '/index.html' if path != '/' else 'index.html')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(document, encoding='utf-8')


def meta(post):
    return f'<div class="meta"><span class="category">{e(post["category"])}</span><span aria-hidden="true">·</span><time datetime="{e(post["date"])}">{e(post["date"].replace("-", "."))}</time></div>'


def tags(values):
    return '<div class="tags">' + ''.join(f'<span class="tag">{e(value)}</span>' for value in values) + '</div>'


def post_row(post):
    return f'<article class="post-row"><div class="thumb">{cover_image(post)}</div><div>{meta(post)}<h3><a href="/posts/{e(post["slug"])}/">{e(post["title"])}</a></h3><div class="card-summary">{post["summary_html"]}</div></div></article>'


def cover_image(item):
    if item.get('image'):
        return f'<img class="content-cover cover-{e(item["image_fit"])}" src="{e(item["image"])}" alt="{e(item["title"])} 的展示图" loading="lazy" decoding="async">'
    return art(item['art'])


def project_card(project):
    path = f'/projects/{project["slug"]}/'
    return f'<article class="project-card"><a class="project-art project-cover-link" href="{path}" aria-label="查看项目：{e(project["title"])}">{cover_image(project)}</a><div class="project-info"><h3><a href="{path}">{e(project["title"])}</a></h3><div class="subtitle">{e(project["subtitle"])}</div><div class="card-summary">{project["summary_html"]}</div>{tags(project["tags"])}<div class="project-actions"><a class="text-link" href="{path}">了解这个项目 →</a>{external(project["url"], "打开项目链接", "text-link")}</div></div></article>'


def head(eyebrow, title, description):
    return f'<div class="page-head"><span class="eyebrow">{e(eyebrow)}</span><h1>{e(title)}</h1><p>{e(description)}</p></div>'


def about_body(profile):
    image = f'<img class="profile-avatar" src="{e(profile["image"])}" alt="{e(profile["name"])} 的头像" decoding="async">' if profile['image'] else avatar()
    links = ''.join(external(profile[key], label) for key, label in [('github', 'GitHub'), ('gitee', 'Gitee')] if profile[key])
    interests = f'<h3>{e(profile["interests_title"])}</h3><div class="interest-list">' + ''.join(f'<span>{e(value)}</span>' for value in profile['interests']) + '</div>' if profile['interests'] else ''
    wishes = f'<h3>{e(profile["wishlist_title"])}</h3><ul class="wish-list">' + ''.join(f'<li><span>{e(wish["label"])}</span><small>{e(wish["status"])}</small></li>' for wish in profile['wishes']) + '</ul>' if profile['wishes'] else ''
    quote = '<blockquote class="about-quote">' + '<br>'.join(e(line) for line in profile['quote'].splitlines()) + '</blockquote>' if profile['quote'] else ''
    return f'<div class="about-grid"><aside class="profile-card"><div class="avatar profile-avatar-frame">{image}</div><h2>{e(profile["name"])}</h2><p>{e(profile["role"])}</p>{tags(profile["tags"])}<div class="social-row">{links}</div></aside><div class="about-copy"><h2>你好，我是 {e(profile["name"])} <span aria-hidden="true">✿</span></h2><div class="prose about-prose">{profile["html"]}</div>{interests}{wishes}{quote}</div></div>'


def contribution_section():
    return f'''<section class="section code-garden" id="code-garden" data-activity aria-labelledby="garden-title">
<div class="section-heading"><div><span class="eyebrow">A LITTLE CODE GARDEN</span><h2 id="garden-title">代码小花园</h2></div><div class="source-switch" role="group" aria-label="贡献数据来源"><button type="button" data-source="all" aria-pressed="true" disabled>总</button><button type="button" data-source="github" aria-pressed="false" disabled>GitHub</button><button type="button" data-source="gitee" aria-pressed="false" disabled>Gitee</button></div></div>
<div class="garden-panel"><div class="garden-summary" aria-live="polite" aria-atomic="true"><div><div class="garden-range" data-calendar-range>正在读取真实数据…</div><div class="garden-total"><strong data-calendar-total>—</strong><span data-calendar-total-label>两平台贡献合计</span></div><div class="garden-breakdown" data-calendar-breakdown>每一格，都是一点小小的积累</div></div><div class="garden-mini-stats"><p><strong data-calendar-active>—</strong><span>天有贡献</span></p><p><strong data-calendar-last>—</strong><span>最近贡献</span></p></div></div>
<p class="calendar-state" data-calendar-state role="status" aria-live="polite">正在同步小花园的记录。</p>
<div class="calendar-scroll" tabindex="0" role="region" aria-label="每日贡献日历，可横向滚动"><div class="calendar-grid" data-calendar-grid></div></div>
<div class="calendar-legend"><p class="calendar-detail" data-calendar-detail>轻触或悬停格子，查看每天的记录。</p><div class="calendar-scale" aria-hidden="true"><span>少</span><i class="cal-day" data-level="0"></i><i class="cal-day" data-level="1"></i><i class="cal-day" data-level="2"></i><i class="cal-day" data-level="3"></i><i class="cal-day" data-level="4"></i><span>多</span></div></div>
<div class="garden-sync"><span>最近成功同步：<span data-calendar-updated>等待首次读取</span></span><span class="garden-schedule">每天凌晨 04:00 自动更新（北京时间）</span></div>
<details class="garden-method"><summary>数据来源与统计说明</summary><div data-calendar-sources><p>{external(SITE['github'], 'GitHub 官方主页')} · {external(SITE['gitee'], 'Gitee 官方主页')}</p></div><p>日历与推送足迹每天凌晨 04:00（北京时间）自动同步，访问和切换平台只展示服务器缓存。日历读取平台官方公开贡献数量，保留平台返回的日期口径。两平台的“最近一年”起止日期可能不同，区间外显示未记录。“总”为已返回贡献相加，同一提交同步到两平台可能重复计入，不代表去重后的代码提交数。同步失败时保留最近成功数据。</p></details>
<details class="push-panel" open><summary><span class="push-title">推送足迹</span><span class="push-count" data-push-count>等待首次采集</span></summary><ul class="push-list" data-push-list></ul><p class="push-source-state" data-push-source-state>公开 Push 事件每天凌晨 04:00（北京时间）采集，平台返回本身可能延迟。</p><p class="push-note" data-push-note>推送记录与官方贡献日历分开统计，未采集时段不按零处理。</p><details class="push-scope-details"><summary data-scope-count>查看采集范围</summary><div data-push-scope></div></details></details>
<noscript><p class="garden-noscript">启用 JavaScript 后可查看贡献日历和切换来源，也可以直接访问上方的官方主页。</p></noscript></div></section>'''


def build(library=None):
    global POSTS, PROJECTS
    library = library or ROOT.parent / 'publications'
    POSTS, PROJECTS, media = load_library(library, markdown)
    profile, about_media = load_about(library, SITE, markdown)
    media.update(about_media)
    OUT.mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'assets', OUT / 'assets', dirs_exist_ok=True)
    for relative, data in media.items():
        target = OUT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    project_cards = ''.join(project_card(project) for project in PROJECTS)
    home = f'''
<section class="hero" aria-labelledby="hello"><div><span class="pill">欢迎来到我的小小世界</span><h1 id="hello">你好，路过的你。<br>一起<em>慢慢生长</em>吧<span class="flower" aria-hidden="true"> ✿</span></h1><p>我是 {e(SITE['name'])}，一个还在探索的大学生。<br>这里收藏代码、学习，和日常里细碎的快乐。</p><div class="actions"><a class="button" href="/articles/">翻开我的手记 <span aria-hidden="true">↗</span></a><a class="text-link" href="/about/">认识一下我 <span aria-hidden="true">→</span></a></div><div class="tiny-note">不必走得很快，只要一直在路上。</div></div><div class="hero-art">{art('garden', label='奶油色的小屋、植物和一只安静的小兔')}</div></section>
<div class="ribbon"><span><i aria-hidden="true">⌁</i> 记录学习，也记录生活</span><span><i aria-hidden="true">▧</i> {len(POSTS):02d} 篇手记，慢慢积累</span><span><i aria-hidden="true">✳</i> 保持好奇，保持热爱</span></div>
{contribution_section()}
<section class="section home-grid" aria-labelledby="latest"><div><div class="section-heading"><div><span class="eyebrow">THE NOTEBOOK</span><h2 id="latest">最近写下的</h2></div><a class="text-link" href="/articles/">所有文章 <span aria-hidden="true">→</span></a></div>{''.join(post_row(post) for post in POSTS[:3])}</div><aside class="home-sidebar"><div class="section-heading"><div><span class="eyebrow">A LITTLE ABOUT ME</span><h2>小屋的主人</h2></div></div><div class="postcard"><div class="mini-art profile-avatar-frame">{avatar()}</div><h3>嗨，很高兴遇见你</h3><p>在大学里学习，也在代码里探索。想把做过的东西、学会的事情，好好收集起来。</p><a class="text-link" href="/about/">关于我的更多碎片 <span aria-hidden="true">→</span></a>{socials()}<div class="handwriting">stay curious, stay gentle.</div></div></aside></section>
<section class="section" aria-labelledby="projects"><div class="section-heading"><div><span class="eyebrow">MADE WITH CURIOSITY</span><h2 id="projects">作品小抽屉</h2></div><a class="text-link" href="/projects/">看看项目 <span aria-hidden="true">→</span></a></div><div class="project-grid">{project_cards}</div></section>
<aside class="garden-note play-invite"><div><span class="eyebrow">TAKE A LITTLE BREAK</span><h3><span aria-hidden="true">✿</span> 在花园里，休息一小会儿</h3><p>翻开花卡，让相同的花朵相遇。没有倒计时，慢慢来也很好。</p></div><a class="button" href="/play/">去玩翻翻乐 ↗</a></aside>
<div class="friends-invite"><span>喜欢的小屋，值得互相串门。</span><a class="text-link" href="/friends/">走走友邻小径 →</a></div>'''
    page('/', '首页', home, 'home')

    categories = ['全部'] + list(dict.fromkeys(post['category'] for post in POSTS))
    filter_buttons = ''.join(f'<button type="button" data-category="{e(category)}" aria-pressed="{str(category == "全部").lower()}">{e(category)}</button>' for category in categories)
    cards = []
    for post in POSTS:
        search = ' '.join([post['title'], post['description'], post['category'], *post['tags']])
        cards.append(f'<article class="archive-card" data-post data-category="{e(post["category"])}" data-search="{e(search)}"><div class="cover">{cover_image(post)}</div><div class="body">{meta(post)}<h2><a href="/posts/{e(post["slug"])}/">{e(post["title"])}</a></h2><div class="card-summary">{post["summary_html"]}</div>{tags(post["tags"])}<a class="text-link" href="/posts/{e(post["slug"])}/" aria-label="阅读：{e(post["title"])}">继续阅读 <span aria-hidden="true">→</span></a></div></article>')
    archive = head('THE NOTEBOOK', '把日子，一页页收藏', '学习时的灵光一闪，写代码时的小小发现，还有平常日子里想记住的事。')
    archive += f'<div class="filters" data-filters hidden><div class="filter-tabs" role="group" aria-label="按文章分类筛选">{filter_buttons}</div><div class="search"><label for="article-search">搜索文章标题、摘要和标签</label><input id="article-search" type="search" placeholder="找找感兴趣的内容…" autocomplete="off"></div></div><div class="archive-summary" data-result role="status" aria-live="polite">共 {len(POSTS)} 篇文章</div><div class="archive-grid">{"".join(cards)}</div><div class="empty" data-empty hidden><h2>这一页，暂时还没写到</h2><p>换个关键词，或者看看其他分类吧。</p><button type="button" data-reset>查看全部文章</button></div>'
    page('/articles/', '文章', archive, 'articles')

    projects = head('THE PROJECT DRAWER', '把想法，做成看得见的东西', '一些代码，一些尝试。这里放着我的公开项目，也放着仍在继续的小小探索。')
    projects += f'<div class="projects-intro"><span>精选 {len(PROJECTS)} 个项目 · 持续整理中</span>{socials()}</div><div class="project-grid">{project_cards}</div><div class="soft-box"><p>更多代码可以到我的 GitHub 和 Gitee 主页逛逛。这里收集项目介绍、详细记录和相关链接；首页的代码小花园已接入官方贡献日历与公开 Push 足迹。</p></div>'
    page('/projects/', '项目', projects, 'projects')

    about = head(profile['eyebrow'], profile['page_title'], profile['description']) + about_body(profile)
    page('/about/', '关于我', about, 'about')

    for post in POSTS:
        for document in post['documents']:
            prose, toc = document['detail']
            toc_html = ''.join(f'<li><a href="#{anchor}">{e(title)}</a></li>' for anchor, title in toc)
            related = ''.join(f'<a href="/posts/{e(other["slug"])}/">{e(other["title"])} <span aria-hidden="true">→</span></a>' for other in POSTS if other['slug'] != post['slug'])
            summary = post['summary_html'] if document['primary'] else ''
            body = f'<div class="breadcrumb"><a href="/articles/">所有文章</a> <span aria-hidden="true"> / </span> {e(post["category"])}</div><header class="article-header">{meta(post)}<h1>{e(document["title"])}</h1><div class="description card-summary">{summary}</div>{tags(post["tags"])}{external(post["url"], "打开文章相关链接", "text-link") if post["url"] else ""}</header><div class="article-layout"><article>{cover_image(post) if post.get("image") and document["primary"] else ""}<div class="prose" lang="{e(document["language"])}">{prose}</div><div class="article-end"><span>写在 {e(SITE["name"])} 的小屋</span><a href="/articles/">返回文章列表 ↑</a></div><div class="related"><span class="eyebrow">KEEP WANDERING</span><h2>再翻一页</h2>{related}</div></article><nav class="toc" aria-label="本文目录"><h2>这一页的小目录</h2><ol>{toc_html}</ol></nav></div>'
            page(document['path'], document['title'], body, 'articles', post['description'])

    for project in PROJECTS:
        for document in project['documents']:
            prose, toc = document['detail']
            toc_html = ''.join(f'<li><a href="#{anchor}">{e(title)}</a></li>' for anchor, title in toc)
            image = f'<div class="detail-media">{cover_image(project)}</div>' if project.get('image') and document['primary'] else ''
            summary = project['summary_html'] if document['primary'] else ''
            project_link = 'Open project' if document['language'] == 'en' else '打开项目链接'
            body = f'<div class="breadcrumb"><a href="/projects/">所有项目</a> <span aria-hidden="true"> / </span> 项目记录</div><header class="article-header"><span class="eyebrow">THE PROJECT STORY</span><h1>{e(document["title"])}</h1><div class="description card-summary">{summary}</div>{tags(project["tags"])}<div class="actions">{external(project["url"], project_link, "button")}</div></header><div class="article-layout"><article>{image}<div class="prose" lang="{e(document["language"])}">{prose}</div><div class="article-end"><span>最近整理于 {e(project["date"])}</span><a href="/projects/">返回项目列表 ↑</a></div></article><nav class="toc" aria-label="项目目录"><h2>这一页的小目录</h2><ol>{toc_html}</ol></nav></div>'
            page(document['path'], document['title'], body, 'projects', project['description'])

    play = head('THE LITTLE PLAYGROUND', '让花朵，慢慢相遇', '读累了就来花园里坐坐。翻开两张花卡，找到藏在这里的八对小小春天。')
    play += '''<section class="memory-layout" data-memory aria-labelledby="game-title"><div class="memory-panel"><div class="memory-heading"><div><span class="eyebrow">FLOWER MEMORY · 01</span><h2 id="game-title">花朵翻翻乐</h2></div><span class="game-badge">一人一小局</span></div><div class="game-stats"><p>已相遇<strong data-pairs>0 / 8</strong></p><p>翻牌步数<strong data-moves>0</strong></p><p>花园时光<strong data-clock>00:00</strong></p></div><div class="memory-board" data-board role="group" aria-label="十六张花卡，点击或用键盘翻开"></div><p class="game-status" data-game-status role="status" aria-live="polite">准备好后，翻开第一张花卡吧。</p><div class="game-actions"><button class="button" type="button" data-new-game hidden>重新种一园 ↻</button><span class="game-best" data-best>本机最佳：等你留下第一份记录</span></div><noscript><p class="soft-box">开启 JavaScript 后就能玩翻翻乐，也可以先去翻翻文章。</p></noscript></div><aside class="game-notes"><div class="game-note-art" aria-hidden="true">✿ <span>✧</span> ❀</div><span class="eyebrow">A MOMENT JUST FOR YOU</span><h2>慢一点，也会开花</h2><p>每次翻开两张卡，相同的花朵会留下，不同的花朵会轻轻合上。找到全部八对，就完成这一园。</p><ul><li>轻触花卡，或用 Tab 和回车操作。</li><li>没有倒计时，也没有失败次数。</li><li>离开当前标签页时暂停计时。</li></ul><p class="game-privacy">最佳成绩只保存在当前浏览器。没有账号，也没有联网排名；清除浏览器数据会重置记录。</p><a class="text-link" href="/articles/">休息好了，去读一页 →</a></aside></section>'''
    page('/play/', '游乐角', play, 'play', '花朵翻翻乐：找到八对花卡，在自己的节奏里休息一会儿。')

    friend_cards = []
    for friend in SITE.get('friends', []):
        if not friend['url'].startswith('https://'):
            raise ValueError('Friend links must use HTTPS')
        friend_cards.append(f'<article class="friend-card"><span class="friend-flower" aria-hidden="true">✿</span><h2>{e(friend["name"])}</h2><p>{e(friend["description"])}</p>{external(friend["url"], "去小屋串门 ↗", "text-link")}</article>')
    friends = head('THE NEIGHBOURHOOD', '走走友邻小径', '互相串门，交换一点灵感。把喜欢的小屋，收进一条温柔的小径。')
    friends += '<section class="friend-grid" aria-label="友邻网站">' + ''.join(friend_cards) + '</section>' if friend_cards else '<div class="friends-empty"><span aria-hidden="true">❀</span><h2>小径刚刚铺好</h2><p>这里还留着一些位置，等下一次相遇。</p></div>'
    friends += f'<section class="house-card" aria-labelledby="house-card-title"><div><span class="eyebrow">A POSTCARD FROM MY HOME</span><h2 id="house-card-title">带走一张小屋名片</h2><p>{e(SITE["description"])}</p><a class="text-link" href="/">回小屋看看 →</a></div><div><label class="sr-only" for="house-card">小屋名称、网址与介绍</label><textarea id="house-card" readonly rows="4">{e(SITE["title"])}\n{e(SITE["url"])}\n{e(SITE["description"])}</textarea><button type="button" class="copy-card" data-copy-card hidden>复制小屋名片</button><span class="copy-state" data-copy-state role="status"></span></div></section>'
    page('/friends/', '友邻小径', friends, 'friends', '喜欢的小屋，值得互相串门。这里是 XingKuiJueLong 的友邻小径。')

    error = f'<div class="error-page"><div class="mini-art">{art("garden")}</div><span class="eyebrow">404 · A LITTLE LOST</span><h1>好像走到花园外面了</h1><p>这一页暂时不存在，回小屋里坐坐吧。</p><div class="actions"><a class="button" href="/">回到首页 →</a><a class="text-link" href="/articles/">翻翻文章</a></div></div>'
    page('/404.html', '这一页迷路了', error, noindex=True)

    # XML is generated with a real serializer so punctuation in content is safe.
    sitemap = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for path in ['/', '/articles/', '/projects/', '/play/', '/friends/', '/about/'] + [document['path'] for item in POSTS + PROJECTS for document in item['documents']]:
        entry = ET.SubElement(sitemap, 'url')
        ET.SubElement(entry, 'loc').text = SITE['url'].rstrip('/') + path
    ET.ElementTree(sitemap).write(OUT / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for key, value in [('title', SITE['title']), ('link', SITE['url']), ('description', SITE['description']), ('language', 'zh-CN')]:
        ET.SubElement(channel, key).text = value
    for post in POSTS:
        item = ET.SubElement(channel, 'item')
        url = SITE['url'].rstrip('/') + f'/posts/{post["slug"]}/'
        for key, value in [('title', post['title']), ('link', url), ('guid', url), ('description', post['description']), ('pubDate', datetime.fromisoformat(post['date']).replace(tzinfo=timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT'))]:
            ET.SubElement(item, key).text = value
    ET.ElementTree(rss).write(OUT / 'feed.xml', encoding='utf-8', xml_declaration=True)
    (OUT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {SITE["url"].rstrip("/")}/sitemap.xml\n', encoding='utf-8')
    print(f'Built {sum(len(item["documents"]) for item in POSTS + PROJECTS) + 7} HTML pages, assets, RSS and sitemap in {OUT}')


if __name__ == '__main__':
    build()
