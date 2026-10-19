// Exercise real game code with a small DOM/clock adapter, without browser storage or dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../assets/memory.js'), 'utf8');
class Element {
  constructor() {
    this.children = []; this.events = {}; this.attrs = {}; this.textContent = '';
    this.className = ''; this.classes = new Set();
    this.classList = {add: n => this.classes.add(n), remove: n => this.classes.delete(n),
      toggle: (n, on) => on ? this.classes.add(n) : this.classes.delete(n)};
  }
  append(...items) { this.children.push(...items); }
  replaceChildren() { this.children = []; }
  setAttribute(name, value) { this.attrs[name] = value; }
  addEventListener(name, handler) { this.events[name] = handler; }
  querySelector(selector) { return this.children.find(e => e.className === selector.slice(1)); }
  click() { this.events.click?.(); }
}
function harness({blocked = false, stored = null} = {}) {
  const fields = Object.fromEntries(['board', 'pairs', 'moves', 'clock', 'best', 'game-status', 'new-game'].map(k => [k, new Element()]));
  const game = new Element();
  game.querySelector = selector => fields[selector.slice(6, -1)];
  const document = {hidden: false, events: {}, querySelector: () => game,
    createElement: () => new Element(), addEventListener(name, fn) { this.events[name] = fn; }};
  let time = 0, id = 0, saved;
  const timeouts = new Map(), intervals = new Map();
  const math = Object.create(Math); math.random = () => 0;
  vm.runInNewContext(source, {document, Math: math, performance: {now: () => time},
    window: {addEventListener() {}},
    localStorage: {getItem() { if (blocked) throw Error('blocked'); return stored; },
      setItem(key, value) { if (blocked) throw Error('blocked'); saved = JSON.parse(value); }},
    setTimeout: fn => { timeouts.set(++id, fn); return id; }, clearTimeout: n => timeouts.delete(n),
    setInterval: fn => { intervals.set(++id, fn); return id; }, clearInterval: n => intervals.delete(n)});
  return {fields, document, game, timeouts, intervals, get saved() { return saved; },
    advance(ms) { time += ms; intervals.forEach(fn => fn()); },
    settle() { const jobs = [...timeouts.values()]; timeouts.clear(); jobs.forEach(fn => fn()); },
    card(index) { return fields.board.children[index]; }};
}
const a = harness();
assert.equal(a.fields.board.children.length, 16);
a.card(0).click(); a.card(0).click();
assert.equal(a.fields.moves.textContent, '0', 'same card cannot make a pair');
a.card(1).click();
assert.equal(a.fields.moves.textContent, 1);
a.card(2).click();
assert.equal(a.card(2).attrs['aria-pressed'], 'false', 'mismatch locks other cards');
a.settle();
assert.equal(a.card(0).attrs['aria-pressed'], 'false');
a.card(0).click(); a.card(1).click(); a.fields['new-game'].click(); a.settle();
assert.equal(a.fields.moves.textContent, '0');
assert.equal(a.timeouts.size, 0, 'restart cancels an old mismatch callback');
a.card(0).click(); a.advance(3000);
a.document.hidden = true; a.document.events.visibilitychange(); a.advance(10000);
assert.equal(a.fields.clock.textContent, '00:03', 'hidden time is excluded');
a.document.hidden = false; a.document.events.visibilitychange(); a.advance(2000);
assert.equal(a.fields.clock.textContent, '00:05');
const b = harness();
const pairs = [[0, 15], [1, 2], [3, 4], [5, 6], [7, 8], [9, 10], [11, 12], [13, 14]];
for (const [x, y] of pairs) { b.card(x).click(); b.advance(1000); b.card(y).click(); }
assert.equal(b.fields.pairs.textContent, '8 / 8');
assert.equal(b.saved.moves, 8); assert.equal(b.saved.seconds, 8);
assert.equal(b.intervals.size, 0, 'completion stops the clock');
b.card(0).click(); assert.equal(b.fields.moves.textContent, 8, 'matched card cannot increase moves');
assert.match(b.fields['game-status'].textContent, /这一园都开花了/);
const c = harness({blocked: true});
for (const [x, y] of pairs) { c.card(x).click(); c.card(y).click(); }
assert.equal(c.fields.pairs.textContent, '8 / 8', 'blocked storage cannot prevent winning');
assert.equal(harness({stored: '{bad json'}).fields.board.children.length, 16);
assert.equal(harness({stored: '{"moves":-1,"seconds":0}'}).fields.best.textContent, '本机最佳：等你留下第一份记录');
console.log('PASS: shuffle/deck, duplicate card, mismatch lock, restart cancellation, visibility pause, completion, local best, blocked/malformed storage');
