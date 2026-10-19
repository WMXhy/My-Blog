#!/usr/bin/env python3
"""Build and validate in isolation, then atomically publish a new static release."""
import argparse
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import shutil
import tempfile
import uuid

import build
import validate

ROOT = Path(__file__).resolve().parent


def publish(check=False):
    with (ROOT / '.publish.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(prefix='blog-publish-') as staging:
            build.OUT = Path(staging) / 'site'
            build.build()
            validate.DIST = build.OUT
            validate.main()
            if check:
                print('检查通过；没有更新线上网站。')
                return
            name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-content-' + uuid.uuid4().hex[:6]
            releases = ROOT / 'releases'
            releases.mkdir(exist_ok=True)
            target = releases / name
            shutil.copytree(build.OUT, target)
            # The previous immutable release is retained for rollback.
            previous = os.readlink(ROOT / 'current') if (ROOT / 'current').is_symlink() else ''
            history = ROOT / 'deploy/publish-history'
            history.mkdir(parents=True, exist_ok=True)
            (history / f'{name}.txt').write_text(previous)
            temporary = ROOT / f'.current-{uuid.uuid4().hex}'
            try:
                temporary.symlink_to('releases/' + name)
                temporary.replace(ROOT / 'current')
            finally:
                temporary.unlink(missing_ok=True)
            print(f'发布成功：https://xingkuijuelong.cn/ （{name}）')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='读取同级 publications 目录，检查通过后更新网站')
    parser.add_argument('--check', action='store_true', help='仅检查，不更新线上网站')
    args = parser.parse_args()
    try:
        publish(args.check)
    except Exception as error:
        raise SystemExit(f'发布未完成，线上旧版本保持不变：{error}') from None
