# 内容格式与发布

**简体中文** · [English](CONTENT.en.md)

真实文稿保存在仓库根目录的 `publications/`，整个目录被 Git 忽略。先运行 `python3 blog/init_content.py` 创建草稿模板；已经有内容时不会覆盖。

```text
publications/
├── articles/
│   ├── _template/          模板，不参与发布
│   └── my-first-post/
└── projects/
    ├── _template/
    └── my-project/
        ├── meta.json
        ├── cover.gif      可选
        ├── link.txt
        ├── summary.md
        ├── content.md
        ├── content.en.md  可选
        └── images/        可选
```

## 元数据

文件夹名使用小写英文、数字、短横线，如 `my-first-post`。标题可以使用中文。文章和项目分别生成 `/posts/<名称>/`、`/projects/<名称>/`；改名会改变网址。

```json
{
  "title": "我的项目",
  "date": "2026-10-19",
  "category": "学习笔记",
  "subtitle": "一句副标题",
  "tags": ["Python", "个人项目"],
  "order": 10,
  "image_fit": "contain",
  "published": false
}
```

`title`、`date` 必填，日期用 `YYYY-MM-DD`。文章按日期从新到旧排列；项目按 `order` 从小到大排列，默认 100。`category` 用于文章，`subtitle` 用于项目。`image_fit` 为 cover（默认，裁切填满）或 contain（完整显示）。模板默认是草稿；设 true 才发布，省略 published 也表示发布。日期不是预约发布时间。

## 文字、链接和图片

- `summary.md`：短介绍，建议 1～3 句话，显示在卡片和详情页。
- `content.md`：详细内容，支持一到三级标题、粗体、链接、本地图片、代码块、简单列表、引用和管道表格。一级标题转为正文二级标题；原始 HTML 被转义，复杂嵌套列表和公式暂不支持。
- `link.txt`：一行完整的 HTTP(S) 地址。文章可留空；项目必填，通常是仓库或演示链接。
- `cover`：只放一张 PNG、JPG/JPEG、GIF 或 WebP；不放时用内置插画。GIF 保留动画，图片内容哈希用于刷新缓存。`.jbg` 仅作为误写的 JPEG 扩展名兼容。
- 正文图片用 `![截图](images/demo.png)`；只引用本内容文件夹内的文件，不用本机盘符或远程图片。文件建议 UTF-8，图片名不含空格。

```markdown
| 动作 | 预览 |
| :--- | :---: |
| 待机 | ![待机](images/idle.gif) |
```

表格在手机上独立横向滚动。代码中的管道和转义的 `\|` 不会错误分列。

## 双语与说明子页

在 content.md 写 `[English](content.en.md)`，英文文件写 `[简体中文](content.md)`。英文文件首行可用 `# English title` 指定详情标题，生成地址为主详情下的 `/en/`。内容不会自动翻译，站点导航仍主要使用中文。

已上传的 Markdown 可用相对链接引用，如 `[说明](docs/install.md)`；`[动画](previews/)` 会读取该目录的 README.md。子页图片相对于子页解析，返回主文稿可写 `../content.md`。目标必须位于同一篇文章/项目内；文件没上传时显示普通文字，不自动获取远程仓库资料。原始 Markdown、脚本和配置不直接公开。

## 发布与撤下

Linux 服务器执行：

```bash
python3 blog/publish.py --check
python3 blog/publish.py
```

程序使用独立临时目录构建和验证，成功后原子切换 current；失败保留旧版本。`_` 或 `.` 开头的文件夹以及 published=false 的草稿不参与构建。撤下时设置 false 并重新发布，旧页面不会混入新快照。

文稿修改后需要手动发布；每天 04:00 的贡献同步只更新数据缓存。内容和活动库应另行备份，Git 仓库不能替代它们的备份。
