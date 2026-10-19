import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import sync


def calendar_days():
    today = datetime.now(sync.CHINA).date()
    return {(today - timedelta(days=364 - n)).isoformat(): (4 if n == 360 else 0) for n in range(365)}


class CalendarTests(unittest.TestCase):
    def test_github_counts_use_tooltip_for_corresponding_date(self):
        days = calendar_days()
        body = '<h2>4 contributions in the last year</h2>'
        for index, (day, count) in enumerate(days.items()):
            body += f'<td class="ContributionCalendar-day" data-date="{day}" id="day-{index}"></td>'
        # Tooltip order deliberately differs from date order.
        for index, count in reversed(list(enumerate(days.values()))):
            body += f'<tool-tip for="day-{index}">{str(count) if count else "No"} contributions on a day.</tool-tip>'
        parser = sync.GitHubCalendar()
        parser.feed(body)
        self.assertEqual(parser.result()['days'], days)

    def test_gitee_sum_matches_official_total(self):
        days = calendar_days()
        body = '<p>最近一年贡献：4 次</p>' + ''.join(f'<div date="{day.replace("-", "")}" data-content="{count}个贡献：{day}"></div>' for day, count in days.items())
        parser = sync.GiteeCalendar()
        parser.feed(body)
        self.assertEqual(parser.result()['total'], 4)

    def test_missing_tooltip_is_failure_not_zero(self):
        parser = sync.GitHubCalendar()
        parser.feed('<h2>0 contributions in the last year</h2><td id="x" class="ContributionCalendar-day" data-date="2026-10-18"></td>')
        with self.assertRaises(ValueError):
            parser.result()

    def test_empty_or_truncated_calendar_is_rejected(self):
        with self.assertRaises(ValueError):
            sync.validate_calendar({}, 0)
        with self.assertRaises(ValueError):
            sync.validate_calendar(calendar_days(), 999)
        truncated = calendar_days()
        del truncated[sorted(truncated)[100]]
        with self.assertRaises(ValueError):
            sync.validate_calendar(truncated, 4)

    def test_duplicate_gitee_dates_are_rejected(self):
        parser = sync.GiteeCalendar()
        item = '<div date="20261018" data-content="0个贡献：2026-10-18"></div>'
        with self.assertRaises(ValueError):
            parser.feed(item + item)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = sync.database(Path(self.directory.name) / 'test.sqlite3')
        self.settings = {'username': 'demo', 'repositories': ['demo/repo'], 'profile': 'https://github.com/demo'}
        self.config = {'platforms': {'github': self.settings, 'gitee': self.settings}}
        self.event = {'id': '42', 'type': 'PushEvent', 'public': True, 'actor': {'login': 'demo'}, 'repo': {'name': 'demo/repo'},
                      'created_at': '2026-10-17T18:00:00Z', 'payload': {'ref': 'refs/heads/main', 'before': 'a' * 40, 'head': 'b' * 40}}

    def tearDown(self):
        self.db.close()
        self.directory.cleanup()

    def test_push_filters(self):
        self.assertIsNotNone(sync.normalize_event('github', self.event, self.settings))
        for change in ('private', 'actor', 'repository', 'tag', 'deleted', 'zero', 'unchanged'):
            event = copy.deepcopy(self.event)
            if change == 'private': event['public'] = False
            if change == 'actor': event['actor']['login'] = 'someone-else'
            if change == 'repository': event['repo']['name'] = 'demo/another'
            if change == 'tag': event['payload']['ref'] = 'refs/tags/v1'
            if change == 'deleted': event['payload']['deleted'] = True
            if change == 'zero': event['payload']['head'] = '0' * 40
            if change == 'unchanged': event['payload']['head'] = event['payload']['before']
            with self.subTest(change=change):
                self.assertIsNone(sync.normalize_event('github', event, self.settings))

    def test_event_ids_are_deduplicated_and_platforms_remain_separate(self):
        result = {'events': [self.event, self.event], 'limited': False}
        with self.db:
            sync.save_success(self.db, 'github', 'events', result, self.settings, sync.now())
            sync.save_success(self.db, 'github', 'events', result, self.settings, sync.now())
            sync.save_success(self.db, 'gitee', 'events', result, self.settings, sync.now())
        self.assertEqual(self.db.execute('SELECT count(*) FROM push_events').fetchone()[0], 2)
        self.assertEqual(self.db.execute('SELECT day FROM push_events LIMIT 1').fetchone()[0], '2026-10-18')

    def test_failure_preserves_last_success_calendar_and_history(self):
        days = calendar_days()
        result = {'days': days, 'start': min(days), 'end': max(days), 'total': 4, 'source_url': 'https://github.com/users/demo/contributions', 'source_kind': 'official_public_calendar_html', 'sha256': 'test'}
        with self.db:
            sync.save_success(self.db, 'github', 'calendar', result, self.settings, sync.now())
        success = sync.get_state(self.db, 'github.calendar')['last_success']
        with self.db:
            sync.save_failure(self.db, 'github', 'calendar', TimeoutError('simulated timeout'), sync.now())
        snapshot = sync.public_snapshot(self.db, self.config)
        value = snapshot['platforms']['github']['calendar']
        self.assertEqual((value['status'], value['total'], value['last_success']), ('stale', 4, success))
        self.assertEqual(value['days'], days)
        self.assertEqual(self.db.execute('SELECT count(*) FROM calendar_snapshots').fetchone()[0], 1)

    def test_first_failure_is_unknown_not_zero(self):
        with self.db:
            sync.save_failure(self.db, 'gitee', 'calendar', ValueError('changed upstream HTML'), sync.now())
        value = sync.public_snapshot(self.db, self.config)['platforms']['gitee']['calendar']
        self.assertEqual(value['status'], 'unavailable')
        self.assertIsNone(value['total'])
        self.assertEqual(value['days'], {})

    def test_no_raw_commit_message_or_email_in_public_json(self):
        self.event['payload']['commits'] = [{'message': 'PRIVATE_TEST_MARKER', 'author': {'email': 'PRIVATE_EMAIL_MARKER'}}]
        with self.db:
            sync.save_success(self.db, 'github', 'events', {'events': [self.event], 'limited': False}, self.settings, sync.now())
        public = json.dumps(sync.public_snapshot(self.db, self.config))
        self.assertNotIn('PRIVATE_TEST_MARKER', public)
        self.assertNotIn('PRIVATE_EMAIL_MARKER', public)

    def test_malformed_batch_rolls_back_instead_of_partial_success(self):
        invalid = copy.deepcopy(self.event)
        invalid['id'] = '43'
        invalid['created_at'] = 'broken'
        with self.assertRaises(ValueError):
            with self.db:
                sync.save_success(self.db, 'github', 'events', {'events': [self.event, invalid], 'limited': False}, self.settings, sync.now())
        self.assertEqual(self.db.execute('SELECT count(*) FROM push_events').fetchone()[0], 0)


class PaginationTests(unittest.TestCase):
    def test_already_collected_page_stops_repeated_history_fetches(self):
        events = [{'id': str(index)} for index in range(100)]
        class Fetch:
            calls = []
            def get(self, url, accept):
                self.calls.append(url)
                if len(self.calls) > 1:
                    raise AssertionError('Known history should not be downloaded again')
                return json.dumps(events)
        fetch = Fetch()
        result = sync.collect_events('gitee', {'username': 'demo'}, fetch, {event['id'] for event in events})
        self.assertEqual(len(fetch.calls), 1)
        self.assertFalse(result['limited'])

    def test_gitee_uses_prev_id_not_page_number(self):
        class Fetch:
            def __init__(self): self.calls = []
            def get(self, url, accept):
                self.calls.append(url)
                return json.dumps([{'id': str(index)} for index in range(100)]) if len(self.calls) == 1 else '[]'
        fetch = Fetch()
        sync.collect_events('gitee', {'username': 'demo'}, fetch)
        self.assertIn('&prev_id=99', fetch.calls[1])


if __name__ == '__main__':
    unittest.main()
