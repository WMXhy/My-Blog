# My-Blog · 一个慢慢生长的个人小屋

**简体中文** · [English](README.en.md)

奶油白、鼠尾草绿和一点豆沙粉。这里是 XingKuiJueLong 的个人博客源码，记录学习、展示作品，也给日常留一个可以休息的角落。

[走进小屋](https://xingkuijuelong.cn/) · [项目介绍](https://xingkuijuelong.cn/projects/my-blog/) · [部署说明](docs/DEPLOYMENT.zh-CN.md) · [内容格式](docs/CONTENT.zh-CN.md)

## 小屋里有什么

- **学习手记**：Markdown 文章、分类、搜索、阅读目录、RSS、站点地图和 404 页面。
- **作品小抽屉**：项目卡片、独立详情页、封面与 GIF 展示、外部仓库链接。
- **代码小花园**：GitHub / Gitee 官方公开贡献日历，支持“总 / GitHub / Gitee”切换；公开 Push 足迹独立统计。
- **轻松一小局**：花朵翻翻乐，16 张卡片配对、计时、本机最佳成绩，离开标签页时暂停。
- **温柔的配色**：奶油白、静夜绿和跟随系统，浏览器记住偏好。
- **友邻小径**：友链卡片与可复制的小屋名片。
- **关于我**：在外部内容目录编辑正文、资料、兴趣、愿望清单和头像，不必修改页面代码。
- **移动端阅读**：日历与表格在各自区域内横向滚动，减少动态效果偏好也会被尊重。

Markdown 支持本地图片、GIF、表格、代码块、基本列表与引用；`content.md` / `content.en.md` 可互相链接并生成中英文详情页。站点导航目前以中文为主，多语言切换针对作者提供的正文，不自动翻译内容。

## 轻量实现

| 部分 | 实现 |
| --- | --- |
| 页面生成 | Python 3.12+ 标准库，无第三方 Python 包 |
| 浏览器交互 | 原生 JavaScript、CSS，本地字体与素材 |
| 网站服务 | Nginx 提供静态文件，不需要常驻 Python / Node 服务 |
| 贡献同步 | Python、SQLite、systemd timer，每天北京时间 04:00 |
| 内容发布 | 临时目录构建、完整链接检查、原子切换发布快照 |

GitHub / Gitee 数据读取公开页面与公开事件接口，不需要账号 Token。贡献数与 Push 次数采用不同口径；“总”是两平台贡献相加，同一提交可能跨平台计入。接口历史有限、页面结构可能变化，失败时保留旧数据，未记录日期不当作零。详见[数据同步说明](docs/ACTIVITY.zh-CN.md)。

## 快速预览

安装 Python 3.12 或更新版本。在仓库根目录运行：

```bash
python3 blog/init_content.py
python3 blog/build.py
python3 blog/validate.py
python3 -m http.server 8000 --directory blog/dist
```

打开 [本地预览](http://localhost:8000)。初始化只创建被 Git 忽略的 `publications/` 和草稿模板，不带入作者的文章与项目，也不会覆盖现有文件。

纯静态预览未提供 `/api/activity` 时，代码小花园会显示数据暂不可用；按部署说明配置缓存接口与采集服务后即可显示真实数据。`publish.py` 与采集程序使用 Linux 文件锁，服务器发布和同步请在 Linux 上运行。

## 写文章、放项目

```text
My-Blog/
├── blog/                         网站程序
├── docs/                         中英文维护说明
├── examples/                     通用草稿模板
└── publications/                 初始化后创建，不进 Git
    ├── articles/my-first-post/   一篇文章一个文件夹
    ├── projects/my-project/      一个项目一个文件夹
    └── about/                   关于我的资料与正文
```

每个内容文件夹包括 `meta.json`、可选的 `cover.png/jpg/gif`、`link.txt`、`summary.md` 和 `content.md`。需要英文版时加 `content.en.md`。复制模板、改名并填好内容，将 `published` 改为 `true` 后，在服务器运行：

```bash
python3 blog/publish.py --check  # 只检查
python3 blog/publish.py          # 检查通过后上线
```

失败时保留线上旧版本。撤下内容只需把 `published` 改回 `false` 再发布。上传文件不会自动触发上线，贡献数据的每日同步也不会替你发布文稿。

“关于我”使用 `publications/about/meta.json`、`content.md` 和可选的 `avatar.jpg/png/gif`，修改后运行同一条发布命令。初始化提供通用示例，真实资料继续保留在被 Git 忽略的目录里。

## 配置与检查

- `blog/site.json`：站点名、网址、个人主页与友链。
- `blog/activity/config.json`：公开账号及需要统计的仓库。
- `blog/build.py`：页面布局与站点特定页脚；复用时替换个人资料与备案信息。
- `blog/deploy/`：Nginx 示例和 systemd 服务、定时器。

```bash
python3 -m unittest discover -s blog/tests -p 'test_*.py' -v
(cd blog/activity && python3 -m unittest -v test_sync)
node blog/tests/memory.test.cjs
```

Node.js 只用于游戏逻辑检查，部署网站本身不依赖 Node。GitHub Actions 会执行上述检查和空内容库构建，真实账号同步由服务器定时任务负责，不在 CI 请求上游平台。

## 仓库范围

仓库保留网站源码、必要静态素材、通用模板、测试和说明；不包含 `publications/` 的文章/项目、SQLite 历史库、HTTP 缓存、构建产物、服务器凭据或实际 TLS 配置。历史的[个人博客建设方案](个人博客建设方案.md)保留作设计背景，当前操作以本 README 与 docs 为准。

评论、账号和联网排行榜暂未接入。游戏成绩与配色仅保存在当前浏览器。
