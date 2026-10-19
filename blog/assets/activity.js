(() => {
  const garden = document.querySelector('[data-activity]');
  if (!garden) return;
  const names = { github: 'GitHub', gitee: 'Gitee' };
  const field = (name) => garden.querySelector(`[data-${name}]`);
  const buttons = [...garden.querySelectorAll('[data-source]')];
  let snapshot;
  let selected = 'all';
  let loading = false;
  const number = (value) => new Intl.NumberFormat('zh-CN').format(value);
  const stamp = (value) => value ? new Date(value).toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  }) : '尚未同步';
  const iso = (day) => day.toISOString().slice(0, 10);
  const parseDay = (text) => new Date(`${text}T00:00:00Z`);
  function missedDailySync(state) {
    // Evaluate the 04:00 Beijing schedule, allowing one hour for a delayed run.
    const beijing = new Date(Date.now() + 8 * 3600000);
    let expected = Date.UTC(beijing.getUTCFullYear(), beijing.getUTCMonth(), beijing.getUTCDate(), 4) - 8 * 3600000;
    if (Date.now() < expected + 3600000) expected -= 86400000;
    return !state.last_success || new Date(state.last_success).getTime() < expected;
  }
  const text = (tag, content, className) => {
    const element = document.createElement(tag);
    element.textContent = content;
    if (className) element.className = className;
    return element;
  };

  function calendarView(keys) {
    const values = keys.map((key) => snapshot.platforms[key].calendar);
    const dates = [...new Set(values.flatMap((value) => Object.keys(value.days || {})))].sort();
    const days = dates.map((day) => {
      const counts = Object.fromEntries(keys.map((key) => [key, snapshot.platforms[key].calendar.days?.[day] ?? null]));
      const known = Object.values(counts).filter((count) => count !== null);
      return { day, counts, total: known.length ? known.reduce((sum, count) => sum + count, 0) : null, partial: known.length !== keys.length };
    });
    return { days, total: days.reduce((sum, day) => sum + (day.total ?? 0), 0), active: days.filter((day) => day.total > 0).length };
  }

  function renderGrid(view, keys) {
    const container = field('calendar-grid');
    container.replaceChildren();
    if (!view.days.length) {
      container.append(text('p', '日历暂未获取成功。同步成功后会在这里显示真实记录。', 'garden-empty'));
      return;
    }
    const entries = new Map(view.days.map((value) => [value.day, value]));
    const first = parseDay(view.days[0].day);
    const last = parseDay(view.days.at(-1).day);
    const start = new Date(first);
    start.setUTCDate(start.getUTCDate() - start.getUTCDay());
    const count = Math.ceil(((last - start) / 86400000 + 1) / 7);
    if (count > 60) throw new Error('Unexpected calendar range');
    const weekday = text('div', '', 'cal-weekdays');
    weekday.setAttribute('aria-hidden', 'true');
    ['', '', '一', '', '三', '', '五', ''].forEach((label) => weekday.append(text('span', label)));
    container.append(weekday);
    const cells = [];
    for (let week = 0; week < count; week += 1) {
      const column = text('div', '', 'cal-week');
      const month = text('span', '', 'cal-month');
      month.setAttribute('aria-hidden', 'true');
      column.append(month);
      for (let row = 0; row < 7; row += 1) {
        const date = new Date(start);
        date.setUTCDate(date.getUTCDate() + week * 7 + row);
        const day = iso(date);
        if (date.getUTCDate() === 1 && date <= last) month.textContent = `${date.getUTCMonth() + 1}月`;
        const value = entries.get(day);
        if (date < first || date > last) {
          column.append(text('span', '', 'cal-day cal-padding'));
          continue;
        }
        const cell = text('button', '', 'cal-day');
        cell.type = 'button';
        cell.tabIndex = -1;
        const n = value?.total ?? null;
        cell.dataset.level = n === null ? 'unknown' : String(n === 0 ? 0 : n <= 2 ? 1 : n <= 5 ? 2 : n <= 9 ? 3 : 4);
        if (value?.partial) cell.classList.add('cal-partial');
        const detail = `${day} · ${keys.map((key) => `${names[key]} ${value?.counts[key] ?? '未记录'}${value?.counts[key] == null ? '' : ' 次'}`).join(' · ')}${keys.length > 1 && n !== null ? ` · 合计 ${n} 次` : ''}${value?.partial ? '（部分来源未返回该日）' : ''}`;
        cell.title = detail;
        cell.setAttribute('aria-label', detail);
        const show = () => { field('calendar-detail').textContent = detail; };
        cell.addEventListener('mouseenter', show);
        cell.addEventListener('focus', show);
        cell.addEventListener('click', show);
        cell.addEventListener('keydown', (event) => {
          const offsets = { ArrowLeft: -7, ArrowRight: 7, ArrowUp: -1, ArrowDown: 1, PageUp: -28, PageDown: 28 };
          let index = cells.indexOf(cell);
          if (event.key === 'Home') index = 0;
          else if (event.key === 'End') index = cells.length - 1;
          else if (event.key in offsets) index += offsets[event.key];
          else return;
          event.preventDefault();
          index = Math.max(0, Math.min(index, cells.length - 1));
          cells.forEach((item) => { item.tabIndex = -1; });
          cells[index].tabIndex = 0;
          cells[index].focus({ preventScroll: true });
          cells[index].scrollIntoView({ block: 'nearest', inline: 'nearest' });
        });
        cells.push(cell);
        column.append(cell);
      }
      container.append(column);
    }
    if (cells.length) cells.at(-1).tabIndex = 0;
    // Keep chronological columns; open at the latest dates on narrow screens.
    requestAnimationFrame(() => {
      const scroll = container.closest('.calendar-scroll');
      scroll.scrollLeft = Math.max(0, scroll.scrollWidth - scroll.clientWidth);
    });
  }

  function renderPushes(keys) {
    const sources = keys.map((key) => ({ key, ...snapshot.platforms[key].pushes }));
    const available = sources.filter((source) => source.last_success);
    field('push-count').textContent = available.length ? `已采集 ${number(sources.reduce((sum, source) => sum + (source.total_observed || 0), 0))} 次` : '等待首次采集';
    const recent = sources.flatMap((source) => (source.recent || []).map((event) => ({ ...event, platform: source.key })))
      .sort((a, b) => b.occurred_at.localeCompare(a.occurred_at)).slice(0, 3);
    const list = field('push-list');
    list.replaceChildren();
    for (const event of recent) {
      const item = text('li', '', 'push-event');
      item.append(text('span', names[event.platform], `push-platform ${event.platform}`));
      const link = text('a', event.repository.split('/').slice(1).join('/'));
      link.href = `https://${event.platform === 'github' ? 'github.com' : 'gitee.com'}/${event.repository.split('/').map(encodeURIComponent).join('/')}`;
      link.target = '_blank'; link.rel = 'noopener noreferrer';
      item.append(link, text('span', event.ref.replace(/^refs\/heads\//, ''), 'push-branch'), text('time', stamp(event.occurred_at)));
      list.append(item);
    }
    if (!recent.length) list.append(text('li', available.length ? '尚未采集到符合范围的推送记录。' : '暂时无法取得推送记录，稍后再来看看。', 'garden-empty'));
    field('push-source-state').textContent = sources.map((source) => `${names[source.key]}：${source.last_success ? `${stamp(source.last_success)}${source.status === 'stale' || missedDailySync(source) ? '（保留上次成功结果）' : ''}` : '待同步'}`).join(' · ');
    const starts = available.map((source) => source.tracking_since).filter(Boolean).sort();
    field('push-note').textContent = `${starts.length ? `采集启用于 ${stamp(starts[0])}。` : ''}已补录接口当前可返回的历史记录；接口有时间与条数限制，未覆盖时段不视为零。只统计所选公开仓库中本人的分支推送，排除删除、标签和重复事件。`;
    const scope = field('push-scope');
    scope.replaceChildren();
    for (const source of sources) {
      scope.append(text('p', `${names[source.key]} · ${source.repositories.length} 个仓库`, 'scope-title'));
      const repositories = text('ul', '', 'scope-repositories');
      source.repositories.forEach((repository) => repositories.append(text('li', repository)));
      scope.append(repositories);
    }
    field('scope-count').textContent = `采集范围：${sources.reduce((sum, source) => sum + source.repositories.length, 0)} 个公开仓库`;
  }

  function render() {
    const keys = selected === 'all' ? ['github', 'gitee'] : [selected];
    const view = calendarView(keys);
    buttons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.source === selected)));
    field('calendar-total').textContent = view.days.length ? number(view.total) : '—';
    const missingSource = keys.some((key) => !Object.keys(snapshot.platforms[key].calendar.days || {}).length);
    field('calendar-total-label').textContent = selected === 'all' ? missingSource ? '已返回平台贡献' : '两平台贡献合计' : `${names[selected]} 公开贡献`;
    field('calendar-active').textContent = view.days.length ? number(view.active) : '—';
    const latest = [...view.days].reverse().find((value) => value.total > 0);
    field('calendar-last').textContent = latest ? latest.day.slice(5).replace('-', '.') : '暂无';
    field('calendar-range').textContent = view.days.length ? `${view.days[0].day} — ${view.days.at(-1).day}` : '等待真实数据同步';
    field('calendar-breakdown').textContent = keys.map((key) => `${names[key]} ${snapshot.platforms[key].calendar.total ?? '待同步'}${snapshot.platforms[key].calendar.total == null ? '' : ' 次'}`).join(' · ');
    const problems = keys.filter((key) => {
      const state = snapshot.platforms[key].calendar;
      return state.status !== 'ok' || missedDailySync(state);
    });
    const partial = view.days.filter((value) => value.partial).length;
    field('calendar-state').textContent = problems.length ? `${problems.map((key) => names[key]).join(' / ')} 暂未完成最新同步，${view.days.length ? '已有数据继续保留' : '尚无可展示记录'}。` : partial ? `${partial} 个日期仅部分平台返回记录，已在格子中标明。` : '官方公开日历已同步';
    field('calendar-state').classList.toggle('is-pending', problems.length > 0);
    field('calendar-detail').textContent = '默认展示最近日期，可向右滑动查看更早记录。轻触格子查看每日贡献，虚线表示部分来源未记录。';
    field('calendar-updated').textContent = keys.map((key) => `${names[key]} ${stamp(snapshot.platforms[key].calendar.last_success)}`).join(' · ');
    const sourceList = field('calendar-sources');
    sourceList.replaceChildren();
    keys.forEach((key) => {
      const item = text('p', `${names[key]}：公开主页贡献日历 · `);
      const link = text('a', '查看官方主页 ↗');
      link.href = snapshot.platforms[key].profile;
      link.target = '_blank'; link.rel = 'noopener noreferrer';
      item.append(link);
      sourceList.append(item);
    });
    renderGrid(view, keys);
    renderPushes(keys);
  }

  async function load() {
    if (loading) return;
    loading = true;
    try {
      const response = await fetch('/api/activity', { cache: 'no-cache', credentials: 'omit', signal: AbortSignal.timeout(12000) });
      if (!response.ok) throw new Error('Activity temporarily unavailable');
      const data = await response.json();
      if (data.schema_version !== 1 || !data.platforms?.github?.calendar || !data.platforms?.gitee?.calendar) throw new Error('Unexpected activity data');
      snapshot = data;
      render();
      buttons.forEach((button) => { button.disabled = false; });
    } catch (error) {
      field('calendar-state').textContent = snapshot ? '暂时无法读取，继续展示当前已加载的数据。' : '真实数据暂时无法读取，请稍后再来或访问官方主页。';
      field('calendar-state').classList.add('is-pending');
    } finally {
      loading = false;
    }
  }
  buttons.forEach((button) => button.addEventListener('click', () => { selected = button.dataset.source; render(); }));
  load();
})();
