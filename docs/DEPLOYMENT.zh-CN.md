# Linux / Nginx 部署

**简体中文** · [English](DEPLOYMENT.en.md)

## 目录与初次发布

下面假设仓库位于 `/www/web/My-Blog`。依赖 Python 3.12+、Nginx；活动同步使用 systemd。无需 pip 安装、数据库服务或常驻应用服务器。

```bash
git clone https://github.com/WMXhy/My-Blog.git /www/web/My-Blog
cd /www/web/My-Blog
python3 blog/init_content.py
python3 blog/publish.py
```

这会发布一个没有作者真实文稿的站点。上传自己的内容见[内容说明](CONTENT.zh-CN.md)。修改 blog/site.json 中的个人资料和域名，并替换 build.py 中的站点特定备案信息及相关图片后，再公开使用。

## Nginx

`blog/deploy/nginx.example.conf` 是静态后端示例，默认仅监听 127.0.0.1:8080。将 root 和缓存 JSON 的绝对路径替换为实际路径：

```text
root  /www/web/My-Blog/blog/current;
alias /www/web/My-Blog/blog/runtime/public/activity.json;
```

宝塔或现有 HTTPS 虚拟主机反向代理到 `http://127.0.0.1:8080`。域名的 80/443 入口及证书在公网虚拟主机配置；不要把 HTTP 反代目标填写成 Nginx 自己的 443 端口。证书和密钥不放进仓库。

检查 Nginx 配置后 reload。Nginx 工作用户需要读取 current 指向的发布目录。示例保留本地 CSP、安全响应头、自定义 404 和 `/api/activity` 缓存接口。

## 活动同步

先编辑 `blog/activity/config.json`。服务文件中的 WorkingDirectory、ExecStart、ReadWritePaths 替换为实际路径，User/Group 改为你的 Nginx 用户（例如 www 或 www-data）。

```bash
mkdir -p blog/runtime/private blog/runtime/public
chown -R www:www blog/runtime
chmod 700 blog/runtime/private
chmod 750 blog/runtime/public
cp blog/deploy/blog-activity-sync.service /etc/systemd/system/
cp blog/deploy/blog-activity-sync.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now blog-activity-sync.timer
systemctl start blog-activity-sync.service
systemctl list-timers blog-activity-sync.timer --no-pager
```

示例命令的 www 应按实际用户修改。timer 使用 `04:00:00 Asia/Shanghai`，服务器时区不同也按北京时间执行；停机错过后恢复时补执行一次。公开缓存由服务用户创建，Nginx 只读取它，私有 SQLite 和 HTTP 缓存不对外提供。

若未配置同步，其他页面仍能阅读，花园会显示缺少数据的状态。不要为了解决缓存读取问题而把整个 runtime 目录公开。

## 更新、回滚与备份

拉取源码前确认本机修改，并备份 publications、blog/site.json、activity/config.json 和运行数据库；仓库拉取不应覆盖你自行维护的配置。新内容发布使用：

```bash
cd /www/web/My-Blog
python3 blog/publish.py --check
python3 blog/publish.py
```

每次发布生成 `blog/releases/<时间>-content-<标识>/`，上一快照路径记录在 `blog/deploy/publish-history/`。回滚时把 current 重新指向保留的旧快照并原子替换链接；不需要清空文稿或数据库。确认回滚内容后再清理旧快照，不自动删除历史。

活动库使用 SQLite WAL，在线备份应使用 sqlite3.Connection.backup()，不要只复制正在写入的主文件。Git 仓库不包含文稿、数据库、HTTP 缓存、服务器信息或 TLS 文件，需另行备份。

## 故障定位

```bash
python3 blog/publish.py --check
systemctl status blog-activity-sync.timer --no-pager
journalctl -u blog-activity-sync.service -n 40 --no-pager
curl -I http://127.0.0.1:8080/
curl -I http://127.0.0.1:8080/api/activity
```

本机静态预览不会提供活动 API。上游页面结构改变时，查看同步日志并维护解析器；不要把解析失败转换为零贡献。
