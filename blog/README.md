# 网站源码

**简体中文** · [English](README.en.md)

完整介绍见[仓库首页](../README.md)。页面生成、文稿加载、活动同步与浏览器交互都位于本目录。

- `build.py`：静态页面生成。
- `library.py`：文章/项目文件夹与相对 Markdown 页面。
- `init_content.py`：初始化仓库根目录中被 Git 忽略的 publications。
- `publish.py`：Linux 上检查并原子发布。
- `validate.py`：页面元信息、本地链接、锚点和图片检查。
- `assets/`：共用样式、主题、花园和小游戏。
- `activity/`：公开贡献日历与 Push 采集，详见[数据说明](../docs/ACTIVITY.zh-CN.md)。
- `deploy/`：可调整的服务、定时器与 Nginx 示例，详见[部署说明](../docs/DEPLOYMENT.zh-CN.md)。

真实文章和项目不在本目录或本仓库，放在同级 publications 中；格式见[内容说明](../docs/CONTENT.zh-CN.md)。
