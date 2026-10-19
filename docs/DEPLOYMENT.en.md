# Linux / Nginx deployment

[简体中文](DEPLOYMENT.zh-CN.md) · **English**

## Checkout and first release

These examples use `/www/web/My-Blog`. Install Python 3.12+ and Nginx; activity collection additionally uses systemd. No pip packages, database server, or persistent application server are required.

```bash
git clone https://github.com/WMXhy/My-Blog.git /www/web/My-Blog
cd /www/web/My-Blog
python3 blog/init_content.py
python3 blog/publish.py
```

The first release has no private editorial content. See the [content guide](CONTENT.en.md) to add entries. Before public reuse, edit blog/site.json, replace the site-specific footer registration in build.py, and replace the personal assets.

## Nginx

`blog/deploy/nginx.example.conf` is a private static backend bound to 127.0.0.1:8080. Replace its document root and cache alias with the actual paths:

```text
root  /www/web/My-Blog/blog/current;
alias /www/web/My-Blog/blog/runtime/public/activity.json;
```

Point the existing public HTTPS virtual host or Baota proxy at `http://127.0.0.1:8080`. Configure public ports, certificates, and HTTPS redirects in that virtual host. Do not point an HTTP proxy back at Nginx's own TLS port 443. Certificates and private keys stay outside the repository.

Validate the Nginx configuration and reload it. Its worker user must be able to read the release behind current. The example includes the local CSP, security headers, custom 404, and `/api/activity` cache endpoint.

## Activity collection

Edit blog/activity/config.json. Adjust WorkingDirectory, ExecStart, and ReadWritePaths in the service to the actual checkout. Set User and Group to the Nginx worker identity, for example www or www-data.

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

Replace www in these commands with the chosen service user. The timer explicitly uses `04:00:00 Asia/Shanghai`, independent of the host timezone. Persistent scheduling catches up after downtime. The service writes normalized public JSON; private SQLite and upstream HTTP caches are never served.

Without collection, the rest of the blog works and the garden shows unavailable data. Do not expose the entire runtime directory to resolve a cache permission problem.

## Updates, rollback, and backups

Before pulling source changes, review local modifications and back up publications, blog/site.json, activity/config.json, and the live database. Preserve locally maintained configuration when integrating updates.

```bash
cd /www/web/My-Blog
python3 blog/publish.py --check
python3 blog/publish.py
```

Each successful publication creates a timestamped blog/releases directory. The preceding release path is saved under blog/deploy/publish-history. Roll back by atomically replacing current with a symlink to a retained release; content and activity history remain intact. Release deletion is not automatic.

SQLite uses WAL. Use sqlite3.Connection.backup() for an online database backup rather than copying only its main file while it is being written. Content, runtime data, server inventory, and TLS files are deliberately excluded from Git and require separate backups.

## Diagnostics

```bash
python3 blog/publish.py --check
systemctl status blog-activity-sync.timer --no-pager
journalctl -u blog-activity-sync.service -n 40 --no-pager
curl -I http://127.0.0.1:8080/
curl -I http://127.0.0.1:8080/api/activity
```

A basic local static server does not provide the activity API. If upstream markup changes, inspect logs and maintain the parser; do not turn a failed sync into zero contributions.
