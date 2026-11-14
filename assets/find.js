(() => {
  const q = document.getElementById('find-q');
  const clear = document.getElementById('find-clear');
  const count = document.getElementById('find-count');
  const empty = document.getElementById('find-empty');
  const cards = [...document.querySelectorAll('.find-card')];
  const groups = [...document.querySelectorAll('[data-group]')];
  const total = cards.length;

  function run() {
    const t = q.value.toLowerCase().trim();
    let shown = 0;
    cards.forEach(c => {
      const hay = (c.textContent + ' ' + (c.dataset.k || '')).toLowerCase();
      const hit = !t || hay.includes(t);
      c.hidden = !hit;
      if (hit) shown++;
    });
    groups.forEach(g => { g.hidden = ![...g.querySelectorAll('.find-card')].some(c => !c.hidden); });
    count.textContent = t ? shown + ' of ' + total + ' resources match' : total + ' resources';
    empty.hidden = shown > 0;
  }
  q.addEventListener('input', run);
  clear.addEventListener('click', () => { q.value = ''; run(); q.focus(); });
  run();
})();
