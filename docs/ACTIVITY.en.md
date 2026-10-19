# Code garden data model

[简体中文](ACTIVITY.zh-CN.md) · **English**

## Contribution calendars

GitHub's public calendar HTML and Gitee's public profile calendar provide dates, daily counts, and platform totals. The parser checks a continuous, reasonable date range and requires daily counts to match the platform total. These are publicly visible results, not a promise to reproduce private activity visible only after signing in.

Total adds both platform counts without cross-platform Commit deduplication. Returned one-year ranges may differ. Unknown dates are distinct from true zero values, and partially covered dates have dashed borders. Public page markup can change; this is not a stable documented personal-calendar API.

## Push events

Public user event APIs are collected independently. Only PushEvents from the configured account and public repositories are accepted. Branch pushes are included; deletion, tag, and unchanged events are excluded. A platform/event-ID primary key prevents duplicate imports.

Push dates use Asia/Shanghai. A Push count is neither a contribution count nor a Commit count. APIs have bounded history and pagination. Initial backfill includes only returned events. Daily polling may miss events if activity is high or the collector is offline beyond the API window; history is not advertised as permanently complete. Cross-platform events remain separate.

## Scheduling and failures

- systemd checks both calendars and events at 04:00 Asia/Shanghai each day.
- The browser reads only the same-origin `/api/activity` cache. Switching source never calls upstream services.
- Conditional HTTP caching, a nonblocking process lock, transactions, and unique event keys limit repeated work.
- JSON is published atomically. A failed fetch or parse preserves previous successful data.
- Before the first successful sync, the UI shows unavailable data rather than an invented zero-filled year.
- Freshness follows the daily schedule with a one-hour allowance. An already-open page is not live-pushed; reopening reads the updated cache.

## Storage and scope

`blog/runtime/private/activity.sqlite3` retains daily observations and event history. Raw upstream responses remain in the private HTTP cache. Public JSON contains normalized counts, provenance, ranges, times, and recent events, excluding Commit messages and email addresses. Private runtime data is outside the web root.

Editing repository scope in blog/activity/config.json does not delete previously stored events. Adding a project presentation folder does not automatically expand collection scope. Back up the database before any migration that redefines historical measurements.

See the [deployment guide](DEPLOYMENT.en.md) for diagnostics. Unit tests use temporary databases and fixtures rather than online account data.
