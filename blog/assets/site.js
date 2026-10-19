document.documentElement.classList.add('js');

const menuButton = document.querySelector('[data-menu]');
const nav = document.querySelector('#main-nav');
if (menuButton && nav) {
  menuButton.hidden = false;
  menuButton.addEventListener('click', () => {
    const open = menuButton.getAttribute('aria-expanded') !== 'true';
    menuButton.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('is-open', open);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && nav.classList.contains('is-open')) {
      nav.classList.remove('is-open');
      menuButton.setAttribute('aria-expanded', 'false');
      menuButton.focus();
    }
  });
}

const copyCard = document.querySelector('[data-copy-card]');
if (copyCard) {
  copyCard.hidden = false;
  copyCard.addEventListener('click', async () => {
    const card = document.querySelector('#house-card');
    const status = document.querySelector('[data-copy-state]');
    try {
      await navigator.clipboard.writeText(card.value);
      status.textContent = '名片已复制，期待下一次串门。';
    } catch {
      card.focus(); card.select();
      status.textContent = '已选中名片，可以长按或按 Ctrl+C 复制。';
    }
  });
}

const filters = document.querySelector('[data-filters]');
if (filters) {
  filters.hidden = false;
  const input = document.querySelector('#article-search');
  const cards = [...document.querySelectorAll('[data-post]')];
  const empty = document.querySelector('[data-empty]');
  const result = document.querySelector('[data-result]');
  const buttons = [...filters.querySelectorAll('[data-category]')];
  let category = '全部';
  function filter() {
    const query = input.value.trim().toLocaleLowerCase();
    let count = 0;
    for (const card of cards) {
      const matches = (category === '全部' || card.dataset.category === category)
        && card.dataset.search.toLocaleLowerCase().includes(query);
      card.hidden = !matches;
      if (matches) count += 1;
    }
    empty.hidden = count > 0;
    result.textContent = `共 ${count} 篇文章`;
  }
  input.addEventListener('input', filter);
  buttons.forEach((button) => button.addEventListener('click', () => {
    category = button.dataset.category;
    buttons.forEach((item) => item.setAttribute('aria-pressed', String(item === button)));
    filter();
  }));
  document.querySelector('[data-reset]').addEventListener('click', () => {
    input.value = '';
    category = '全部';
    buttons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.category === '全部')));
    filter();
    input.focus();
  });
}
