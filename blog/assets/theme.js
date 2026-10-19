(() => {
  const storageKey = 'little-house-theme';
  const choices = ['light', 'dark', 'system'];
  const system = matchMedia('(prefers-color-scheme: dark)');
  let preference = 'light';
  try {
    const saved = localStorage.getItem(storageKey);
    if (choices.includes(saved)) preference = saved;
  } catch { /* Themes remain usable when browser storage is unavailable. */ }
  function apply() {
    const dark = preference === 'dark' || (preference === 'system' && system.matches);
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#202920' : '#faf8f2');
    const toggle = document.querySelector('[data-theme-toggle]');
    if (toggle) {
      toggle.hidden = false;
      toggle.textContent = dark ? '☀' : '☾';
      toggle.setAttribute('aria-label', dark ? '切换到奶油白配色' : '切换到静夜绿配色');
      toggle.title = dark ? '切换到奶油白' : '切换到静夜绿';
    }
    const select = document.querySelector('[data-theme-choice]');
    if (select) {
      select.value = preference;
      select.closest('.theme-preference').hidden = false;
    }
  }
  function change(value) {
    preference = choices.includes(value) ? value : 'light';
    try { localStorage.setItem(storageKey, preference); } catch { /* Current page still updates. */ }
    apply();
  }
  apply();
  system.addEventListener('change', () => { if (preference === 'system') apply(); });
  window.addEventListener('storage', (event) => {
    if (event.key === storageKey || event.key === null) {
      preference = choices.includes(event.newValue) ? event.newValue : 'light';
      apply();
    }
  });
  document.addEventListener('DOMContentLoaded', () => {
    apply();
    document.querySelector('[data-theme-toggle]')?.addEventListener('click', () => {
      change(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
    });
    document.querySelector('[data-theme-choice]')?.addEventListener('change', (event) => change(event.target.value));
  });
})();
