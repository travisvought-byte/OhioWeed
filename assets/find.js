(() => {
  const q = document.getElementById('find-q');
  const clear = document.getElementById('find-clear');
  const count = document.getElementById('find-count');
  const empty = document.getElementById('find-empty');
  const scopeBox = document.getElementById('find-scope');
  const cards = [...document.querySelectorAll('.find-card')];
  const groups = [...document.querySelectorAll('[data-group]')];
  const total = cards.length;

  // The home page sends people here already pointed at one audience, e.g.
  // find.html?for=grow. Typing in the search box searches everything again,
  // because someone who starts narrow often turns out to want the rest.
  const LABELS = {
    buy: 'things to do with buying',
    grow: 'growing at home',
    law: 'the law and changing it',
    business: 'running a business',
    about: 'this guide'
  };
  const params = new URLSearchParams(location.search);
  let scope = params.get('for');
  if (!LABELS[scope]) scope = null;

  // The header search box on every page is a GET form pointed here, so a
  // search started anywhere on the site arrives as ?q= and is already run.
  const handoff = (params.get('q') || '').slice(0, 80);
  if (handoff) { q.value = handoff; scope = null; }

  function inScope(card) {
    if (!scope) return true;
    const g = card.closest('[data-group]');
    return !!g && g.dataset.for === scope;
  }

  function run() {
    const t = q.value.toLowerCase().trim();
    const scoped = scope && !t;
    let shown = 0;
    cards.forEach(c => {
      const hay = (c.textContent + ' ' + (c.dataset.k || '')).toLowerCase();
      const hit = (!t || hay.includes(t)) && (!scoped || inScope(c));
      c.hidden = !hit;
      if (hit) shown++;
    });
    groups.forEach(g => { g.hidden = ![...g.querySelectorAll('.find-card')].some(c => !c.hidden); });

    if (scopeBox) {
      scopeBox.hidden = !scoped;
      if (scoped) {
        scopeBox.innerHTML = '';
        const label = document.createElement('span');
        label.textContent = 'Showing ' + LABELS[scope] + '.';
        const all = document.createElement('button');
        all.type = 'button';
        all.className = 'find-scope-clear';
        all.textContent = 'Show all ' + total + ' resources';
        all.addEventListener('click', () => { scope = null; run(); });
        scopeBox.append(label, all);
      }
    }

    if (t) count.textContent = shown + ' of ' + total + ' resources match';
    else if (scoped) count.textContent = shown + ' resources';
    else count.textContent = total + ' resources';
    empty.hidden = shown > 0;
  }

  q.addEventListener('input', run);
  clear.addEventListener('click', () => { q.value = ''; run(); q.focus(); });
  run();
})();
