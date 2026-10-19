(() => {
  const game = document.querySelector('[data-memory]');
  if (!game) return;
  const board = game.querySelector('[data-board]');
  const field = (name) => game.querySelector(`[data-${name}]`);
  const flowers = [ ['🌸', '樱花'], ['🌷', '郁金香'], ['🌻', '向日葵'], ['🌼', '雏菊'],
    ['🌹', '玫瑰'], ['🌺', '扶桑花'], ['🪷', '莲花'], ['🪻', '风信子'] ];
  const bestKey = 'little-house-flower-best-v1';
  let cards = [], flipped = [], moves = 0, matched = 0, locked = false, started = false;
  let elapsed = 0, runningSince = null, mismatchTimer = null, clockTimer = null, best = null;
  const duration = () => Math.floor((elapsed + (runningSince === null ? 0 : performance.now() - runningSince)) / 1000);
  const format = (seconds) => `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
  try {
    const saved = JSON.parse(localStorage.getItem(bestKey));
    if (saved && Number.isSafeInteger(saved.moves) && saved.moves >= 8 && saved.moves <= 1000000
        && Number.isSafeInteger(saved.seconds) && saved.seconds >= 0 && saved.seconds <= 31536000) best = saved;
  } catch { /* A blocked or malformed local record never prevents a game. */ }
  function showBest() {
    field('best').textContent = best ? `本机最佳：${best.moves} 步 · ${format(best.seconds)}` : '本机最佳：等你留下第一份记录';
  }
  function pauseClock() {
    if (runningSince !== null) elapsed += performance.now() - runningSince;
    runningSince = null;
    clearInterval(clockTimer);
    field('clock').textContent = format(duration());
  }
  function resumeClock() {
    if (!started || matched === 8 || document.hidden || runningSince !== null) return;
    runningSince = performance.now();
    clockTimer = setInterval(() => { field('clock').textContent = format(duration()); }, 1000);
  }
  function showCard(index, visible) {
    const card = cards[index];
    card.element.classList.toggle('is-open', visible);
    card.element.querySelector('.card-flower').textContent = visible ? flowers[card.kind][0] : '✿';
    card.element.querySelector('.card-caption').textContent = visible ? flowers[card.kind][1] : '小小花园';
    card.element.setAttribute('aria-label', `第 ${index + 1} 张，${visible ? flowers[card.kind][1] : '未翻开'}`);
    card.element.setAttribute('aria-pressed', String(visible));
  }
  function finish() {
    pauseClock();
    const seconds = duration();
    const record = !best || moves < best.moves || (moves === best.moves && seconds < best.seconds);
    if (record) {
      best = { moves, seconds };
      try { localStorage.setItem(bestKey, JSON.stringify(best)); } catch { /* Best remains available for this visit. */ }
      showBest();
    }
    field('game-status').textContent = `这一园都开花了！用了 ${moves} 步，${format(seconds)}。${record ? '留下了一份新的本机最佳记录。' : '谢谢你陪花朵慢慢相遇。'}`;
    game.classList.add('is-complete');
    field('new-game').textContent = '再种一园 ✿';
  }
  function flip(index) {
    const card = cards[index];
    if (locked || card.matched || flipped.includes(index)) return;
    if (!started) { started = true; resumeClock(); }
    showCard(index, true);
    flipped.push(index);
    if (flipped.length === 1) {
      field('game-status').textContent = `是${flowers[card.kind][1]}，找找它的另一半吧。`;
      return;
    }
    moves += 1;
    field('moves').textContent = moves;
    const [a, b] = flipped;
    if (cards[a].kind === cards[b].kind) {
      for (const n of flipped) {
        cards[n].matched = true;
        cards[n].element.classList.add('is-matched');
        cards[n].element.setAttribute('aria-disabled', 'true');
        cards[n].element.setAttribute('aria-label', `第 ${n + 1} 张，${flowers[card.kind][1]}，已配对`);
      }
      matched += 1;
      field('pairs').textContent = `${matched} / 8`;
      flipped = [];
      field('game-status').textContent = `两朵${flowers[card.kind][1]}相遇了！已找到 ${matched} 对。`;
      if (matched === 8) finish();
    } else {
      locked = true;
      field('game-status').textContent = '还不是同一种花，记住它们的位置，再试一次。';
      mismatchTimer = setTimeout(() => {
        showCard(a, false); showCard(b, false);
        flipped = []; locked = false; mismatchTimer = null;
      }, 950);
    }
  }
  function newGame() {
    clearTimeout(mismatchTimer);
    pauseClock();
    elapsed = 0; started = false; locked = false; moves = 0; matched = 0; flipped = [];
    const deck = flowers.flatMap((_, kind) => [kind, kind]);
    for (let n = deck.length - 1; n > 0; n -= 1) {
      const j = Math.floor(Math.random() * (n + 1));
      [deck[n], deck[j]] = [deck[j], deck[n]];
    }
    board.replaceChildren();
    cards = deck.map((kind, index) => {
      const element = document.createElement('button');
      element.type = 'button'; element.className = 'memory-card';
      const flower = document.createElement('span'); flower.className = 'card-flower'; flower.setAttribute('aria-hidden', 'true');
      const caption = document.createElement('span'); caption.className = 'card-caption'; caption.setAttribute('aria-hidden', 'true');
      element.append(flower, caption);
      element.addEventListener('click', () => flip(index));
      board.append(element);
      return { kind, element, matched: false };
    });
    cards.forEach((_, index) => showCard(index, false));
    field('pairs').textContent = '0 / 8'; field('moves').textContent = '0'; field('clock').textContent = '00:00';
    field('game-status').textContent = '准备好后，翻开第一张花卡吧。';
    field('new-game').textContent = '重新种一园 ↻';
    game.classList.remove('is-complete');
    showBest();
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden) pauseClock(); else resumeClock(); });
  window.addEventListener('pagehide', pauseClock);
  window.addEventListener('pageshow', resumeClock);
  field('new-game').hidden = false;
  field('new-game').addEventListener('click', newGame);
  newGame();
})();
