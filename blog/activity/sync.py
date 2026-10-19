#!/usr/bin/env python3
"""Collect public contribution calendars and PushEvents; never execute source HTML/JS."""
from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHINA = timezone(timedelta(hours=8))
USER_AGENT = 'XingKuiJueLong-Blog/1.0 (+https://xingkuijuelong.cn)'
MAX_RESPONSE = 4 * 1024 * 1024


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def atomic_write(path, data, mode=0o640):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Fetcher:
    def __init__(self, directory, timeout=20):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout

    def get(self, url, accept='text/html'):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or parsed.netloc not in ('github.com', 'api.github.com', 'gitee.com'):
            raise ValueError('Unexpected upstream origin')
        key = hashlib.sha256(url.encode()).hexdigest()
        body_file = self.directory / (key + '.body')
        meta_file = self.directory / (key + '.json')
        try:
            cached = json.loads(meta_file.read_text())
        except (OSError, ValueError):
            cached = {}
        headers = {'User-Agent': USER_AGENT, 'Accept': accept, 'Accept-Language': 'en-US,en;q=0.9'}
        if cached.get('etag') and body_file.exists():
            headers['If-None-Match'] = cached['etag']
        if cached.get('last_modified') and body_file.exists():
            headers['If-Modified-Since'] = cached['last_modified']
        request = urllib.request.Request(url, headers=headers)
        try:
            response = urllib.request.urlopen(request, timeout=self.timeout)
        except urllib.error.HTTPError as error:
            if error.code == 304 and body_file.exists():
                return body_file.read_bytes().decode('utf-8')
            raise
        with response:
            if urllib.parse.urlsplit(response.geturl()).netloc not in ('github.com', 'api.github.com', 'gitee.com'):
                raise ValueError('Unexpected redirect origin')
            body = response.read(MAX_RESPONSE + 1)
            if len(body) > MAX_RESPONSE:
                raise ValueError('Upstream response exceeds size limit')
            decoded = body.decode('utf-8')
            metadata = {'etag': response.headers.get('ETag'), 'last_modified': response.headers.get('Last-Modified')}
        atomic_write(body_file, body)
        atomic_write(meta_file, json.dumps(metadata).encode())
        return decoded


class GiteeCalendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        match = re.fullmatch(r'(\d+)个贡献：(\d{4}-\d{2}-\d{2})', attrs.get('data-content', ''))
        if match:
            day = match[2]
            date.fromisoformat(day)
            if attrs.get('date') != day.replace('-', '') or day in self.days:
                raise ValueError('Invalid or duplicate Gitee date')
            self.days[day] = int(match[1])

    def handle_data(self, data):
        self.text.append(data)

    def result(self):
        summary = re.search(r'最近一年贡献：\s*([\d,]+)\s*次', ' '.join(self.text))
        if not summary:
            raise ValueError('Missing Gitee official total')
        return validate_calendar(self.days, int(summary[1].replace(',', '')))


class GitHubCalendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells, self.tips, self.text = {}, {}, []
        self.tip_id = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('data-date') and 'ContributionCalendar-day' in attrs.get('class', '').split():
            day = attrs['data-date']
            date.fromisoformat(day)
            if not attrs.get('id') or day in self.cells.values():
                raise ValueError('Invalid or duplicate GitHub date')
            self.cells[attrs['id']] = day
        if tag == 'tool-tip':
            self.tip_id = attrs.get('for')
            if self.tip_id:
                self.tips[self.tip_id] = []

    def handle_endtag(self, tag):
        if tag == 'tool-tip':
            self.tip_id = None

    def handle_data(self, data):
        self.text.append(data)
        if self.tip_id:
            self.tips[self.tip_id].append(data)

    def result(self):
        days = {}
        for identifier, day in self.cells.items():
            label = ' '.join(self.tips.get(identifier, []))
            count = re.search(r'\b(No|[\d,]+) contributions?\b', label)
            if not count:
                raise ValueError('GitHub daily contribution count missing')
            days[day] = 0 if count[1] == 'No' else int(count[1].replace(',', ''))
        text = re.sub(r'\s+', ' ', ' '.join(self.text))
        summary = re.search(r'([\d,]+) contributions? in the last year', text)
        if not summary:
            raise ValueError('Missing GitHub official total')
        return validate_calendar(days, int(summary[1].replace(',', '')))


def validate_calendar(days, official_total):
    keys = sorted(days)
    if not 300 <= len(keys) <= 400:
        raise ValueError('Unexpected calendar date count')
    if (date.fromisoformat(keys[-1]) - date.fromisoformat(keys[0])).days + 1 != len(keys):
        raise ValueError('Calendar has missing dates')
    if any(not isinstance(n, int) or n < 0 for n in days.values()):
        raise ValueError('Invalid contribution count')
    if sum(days.values()) != official_total:
        raise ValueError('Daily sum differs from official contribution total')
    if abs((datetime.now(CHINA).date() - date.fromisoformat(keys[-1])).days) > 3:
        raise ValueError('Calendar is unexpectedly old')
    return {'days': dict(sorted(days.items())), 'total': official_total, 'start': keys[0], 'end': keys[-1]}


def collect_calendar(platform, config, fetcher):
    user = urllib.parse.quote(config['username'], safe='')
    if platform == 'github':
        source = f'https://github.com/users/{user}/contributions'
        parser = GitHubCalendar()
    else:
        source = f'https://gitee.com/{user}'
        parser = GiteeCalendar()
    body = fetcher.get(source)
    parser.feed(body)
    result = parser.result()
    result.update(source_url=source, source_kind='official_public_calendar_html', sha256=hashlib.sha256(body.encode()).hexdigest())
    return result


def collect_events(platform, config, fetcher, known_ids=None):
    user = urllib.parse.quote(config['username'], safe='')
    events, cursor = [], None
    limited = False
    # GitHub exposes at most 300 recent events; Gitee uses a prev_id cursor.
    max_pages = 3 if platform == 'github' else 5
    for page in range(1, max_pages + 1):
        if platform == 'github':
            url = f'https://api.github.com/users/{user}/events/public?per_page=100&page={page}'
        else:
            url = f'https://gitee.com/api/v5/users/{user}/events/public?limit=100'
            if cursor:
                url += '&prev_id=' + urllib.parse.quote(cursor, safe='')
        batch = json.loads(fetcher.get(url, 'application/json'))
        if not isinstance(batch, list):
            raise ValueError('Unexpected public events response')
        events.extend(batch)
        if len(batch) < 100 or (known_ids and all(str(event.get('id', '')) in known_ids for event in batch)):
            break
        next_cursor = str(batch[-1].get('id', ''))
        if not next_cursor or next_cursor == cursor:
            raise ValueError('Event pagination did not advance')
        cursor = next_cursor
        limited = page == max_pages
    return {'events': events, 'limited': limited}


def normalize_event(platform, event, config):
    if event.get('type') != 'PushEvent' or event.get('public') is not True:
        return None
    actor = (event.get('actor') or {}).get('login', '')
    if actor.casefold() != config['username'].casefold() or actor.endswith('[bot]'):
        return None
    repo_data, payload = event.get('repo') or {}, event.get('payload') or {}
    repository = repo_data.get('full_name') or repo_data.get('name', '')
    if repository.casefold() not in {r.casefold() for r in config['repositories']}:
        return None
    ref = payload.get('ref', '')
    before, after = payload.get('before', ''), payload.get('after') or payload.get('head', '')
    if not isinstance(ref, str) or not ref.startswith('refs/heads/'):
        return None
    if payload.get('deleted') or not after or set(after) == {'0'} or before == after:
        return None
    identifier = str(event.get('id', ''))
    if not identifier or len(identifier) > 100:
        return None
    timestamp = datetime.fromisoformat(event['created_at'].replace('Z', '+00:00'))
    if timestamp.tzinfo is None:
        raise ValueError('Push event must have a timezone')
    return {'id': identifier, 'repository': repository, 'actor': actor, 'ref': ref, 'before': before,
            'after': after, 'occurred_at': timestamp.astimezone(timezone.utc).isoformat(),
            'day': timestamp.astimezone(CHINA).date().isoformat()}


def database(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('PRAGMA busy_timeout=10000')
    connection.executescript('''
        CREATE TABLE IF NOT EXISTS states (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS calendar_days (
            platform TEXT NOT NULL, day TEXT NOT NULL, count INTEGER NOT NULL CHECK(count>=0),
            first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, PRIMARY KEY(platform,day));
        CREATE TABLE IF NOT EXISTS calendar_snapshots (
            id INTEGER PRIMARY KEY, platform TEXT NOT NULL, checked_at TEXT NOT NULL,
            start TEXT NOT NULL, end TEXT NOT NULL, total INTEGER NOT NULL, sha256 TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS push_events (
            platform TEXT NOT NULL, event_id TEXT NOT NULL, repository TEXT NOT NULL, actor TEXT NOT NULL,
            ref TEXT NOT NULL, before_sha TEXT NOT NULL, after_sha TEXT NOT NULL,
            occurred_at TEXT NOT NULL, day TEXT NOT NULL, first_seen TEXT NOT NULL,
            PRIMARY KEY(platform,event_id));
        CREATE TABLE IF NOT EXISTS sync_runs (
            id INTEGER PRIMARY KEY, platform TEXT NOT NULL, kind TEXT NOT NULL, checked_at TEXT NOT NULL,
            success INTEGER NOT NULL, count INTEGER NOT NULL, message TEXT);
        CREATE INDEX IF NOT EXISTS pushes_day ON push_events(platform,day);
    ''')
    return connection


def get_state(db, key):
    row = db.execute('SELECT value FROM states WHERE key=?', (key,)).fetchone()
    return json.loads(row[0]) if row else {}


def set_state(db, key, value):
    db.execute('INSERT INTO states VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
               (key, json.dumps(value, ensure_ascii=False)))


def save_success(db, platform, kind, result, config, checked_at):
    state = get_state(db, f'{platform}.{kind}')
    state.update(last_attempt=checked_at, last_success=checked_at, error=None, failures=0)
    if kind == 'calendar':
        for day, count in result['days'].items():
            db.execute('''INSERT INTO calendar_days VALUES (?,?,?,?,?) ON CONFLICT(platform,day)
                          DO UPDATE SET count=excluded.count,last_seen=excluded.last_seen''',
                       (platform, day, count, checked_at, checked_at))
        db.execute('INSERT INTO calendar_snapshots(platform,checked_at,start,end,total,sha256) VALUES (?,?,?,?,?,?)',
                   (platform, checked_at, result['start'], result['end'], result['total'], result['sha256']))
        state.update({key: result[key] for key in ('start', 'end', 'total', 'source_url', 'source_kind')})
        count = len(result['days'])
    else:
        state.setdefault('tracking_since', checked_at)
        count = 0
        for event in result['events']:
            try:
                item = normalize_event(platform, event, config)
            except (ValueError, TypeError, KeyError):
                # A malformed batch is a failed sync, not a silently incomplete success.
                raise ValueError('Malformed public PushEvent') from None
            if item:
                cursor = db.execute('INSERT OR IGNORE INTO push_events VALUES (?,?,?,?,?,?,?,?,?,?)',
                                    (platform, item['id'], item['repository'], item['actor'], item['ref'],
                                     item['before'], item['after'], item['occurred_at'], item['day'], checked_at))
                count += cursor.rowcount
        state.update(limited=result['limited'], method='public_events_polling', interval_seconds=86400)
    set_state(db, f'{platform}.{kind}', state)
    db.execute('INSERT INTO sync_runs(platform,kind,checked_at,success,count) VALUES (?,?,?,?,?)',
               (platform, kind, checked_at, 1, count))


def save_failure(db, platform, kind, error, checked_at):
    state = get_state(db, f'{platform}.{kind}')
    # Keep all last-success fields and persisted calendar rows on any failure.
    message = f'{type(error).__name__}: {str(error)[:180]}'
    state.update(last_attempt=checked_at, error=True, failures=state.get('failures', 0) + 1)
    set_state(db, f'{platform}.{kind}', state)
    db.execute('INSERT INTO sync_runs(platform,kind,checked_at,success,count,message) VALUES (?,?,?,?,?,?)',
               (platform, kind, checked_at, 0, 0, message))


def public_snapshot(db, config):
    result = {'schema_version': 1, 'generated_at': now(), 'timezone': 'Asia/Shanghai',
              'today': datetime.now(CHINA).date().isoformat(), 'platforms': {}}
    for platform, settings in config['platforms'].items():
        calendar_state = get_state(db, f'{platform}.calendar')
        event_state = get_state(db, f'{platform}.events')
        calendar = {k: calendar_state.get(k) for k in ('last_attempt', 'last_success', 'start', 'end', 'total', 'source_url', 'source_kind')}
        calendar['status'] = 'unavailable' if not calendar_state.get('last_success') else 'stale' if calendar_state.get('error') else 'ok'
        calendar['days'] = {row['day']: row['count'] for row in db.execute(
            'SELECT day,count FROM calendar_days WHERE platform=? AND day>=? AND day<=? ORDER BY day',
            (platform, calendar_state.get('start', ''), calendar_state.get('end', '')))}
        pushes = {k: event_state.get(k) for k in ('last_attempt', 'last_success', 'tracking_since', 'limited', 'method', 'interval_seconds')}
        pushes['status'] = 'unavailable' if not event_state.get('last_success') else 'stale' if event_state.get('error') else 'ok'
        pushes['repositories'] = settings['repositories']
        # Public output is intentionally normalized: no commit messages, email addresses or raw payloads.
        pushes['total_observed'] = db.execute('SELECT count(*) FROM push_events WHERE platform=?', (platform,)).fetchone()[0]
        pushes['recent'] = [dict(row) for row in db.execute(
            'SELECT repository,ref,occurred_at,day FROM push_events WHERE platform=? ORDER BY occurred_at DESC LIMIT 6', (platform,))]
        pushes['observed_days'] = {row['day']: row['count'] for row in db.execute(
            'SELECT day,count(*) AS count FROM push_events WHERE platform=? GROUP BY day ORDER BY day', (platform,))}
        result['platforms'][platform] = {'username': settings['username'], 'profile': settings['profile'], 'calendar': calendar, 'pushes': pushes}
    return result


def run(root, force=False):
    root = Path(root)
    config = json.loads((root / 'activity/config.json').read_text(encoding='utf-8'))
    for settings in config['platforms'].values():
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', settings['username']):
            raise ValueError('Invalid configured username')
    private, public = root / 'runtime/private', root / 'runtime/public'
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    public.mkdir(parents=True, exist_ok=True, mode=0o750)
    os.chmod(private, 0o700)
    with (private / 'sync.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Activity sync already running')
            return
        db = database(private / 'activity.sqlite3')
        fetcher = Fetcher(private / 'http-cache', config.get('request_timeout_seconds', 20))
        futures = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for platform, settings in config['platforms'].items():
                state = get_state(db, f'{platform}.calendar')
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(state['last_attempt'])).total_seconds() if state.get('last_attempt') else float('inf')
                if force or age >= config.get('calendar_interval_seconds', 86400):
                    futures[pool.submit(collect_calendar, platform, settings, fetcher)] = (platform, 'calendar')
                known_ids = {row[0] for row in db.execute('SELECT event_id FROM push_events WHERE platform=?', (platform,))}
                futures[pool.submit(collect_events, platform, settings, fetcher, known_ids)] = (platform, 'events')
            for future in concurrent.futures.as_completed(futures):
                platform, kind = futures[future]
                checked_at = now()
                try:
                    value = future.result()
                    with db:
                        save_success(db, platform, kind, value, config['platforms'][platform], checked_at)
                    print(f'{platform}.{kind}: OK', flush=True)
                except Exception as error:
                    with db:
                        save_failure(db, platform, kind, error, checked_at)
                    print(f'{platform}.{kind}: {type(error).__name__}', flush=True)
        with db:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            db.execute('DELETE FROM sync_runs WHERE checked_at < ?', (cutoff,))
        snapshot = public_snapshot(db, config)
        atomic_write(public / 'activity.json', json.dumps(snapshot, ensure_ascii=False, separators=(',', ':')).encode())
        db.close()
        print('Saved cached activity snapshot', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    run(args.root, args.force)
