(() => {
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const $ = id => document.getElementById(id);
  const NS = 'http://www.w3.org/2000/svg';
  const DCC = 'https://com.ohio.gov/divisions-and-programs/cannabis-control';
  const BASE_R = 7;

  let rows = [], dots = [], active = -1, svg = null, geo = null;
  let view = null, countyShapes = {};

  const norm = r => ({
    name: r.name, city: r.city || '', county: r.county || '', address: r.address || '',
    zip: r.postal_code || '', phone: r.snapshot_phone || '',
    lic: (r.license || {}).number || '', kind: (r.license || {}).kind || '',
    lat: r.latitude, lon: r.longitude,
    src: ((r.sources || [])[0] || {}).source_url || '',
    seen: ((r.sources || [])[0] || {}).recorded_on || ''
  });

  const place = x => [x.address, x.city, x.county && x.county + ' County', x.zip].filter(Boolean).join(' · ');

  // Nudge coincident points apart so every dispensary stays clickable in dense metros.
  function spread(pts) {
    const placed = [];
    return pts.map(pt => {
      if (!pt) return null;
      let [x, y] = pt;
      for (let step = 0; step < 24; step++) {
        if (!placed.some(q => Math.hypot(q[0] - x, q[1] - y) < 5)) break;
        const a = step * 2.4, rad = 3 + step * 1.1;
        x = pt[0] + Math.cos(a) * rad; y = pt[1] + Math.sin(a) * rad;
      }
      placed.push([x, y]);
      return [x, y];
    });
  }

  function sizeDots() {
    const zoom = view ? view[2] / geo.width : 1;
    dots.forEach((d, i) => {
      if (!d) return;
      const mult = i === active ? 1.7 : 1;
      d.setAttribute('r', (BASE_R * zoom * mult).toFixed(2));
    });
  }

  function setView(box, animate) {
    const target = box || [0, 0, geo.width, geo.height];
    if (!view || !animate) { view = target; svg.setAttribute('viewBox', target.join(' ')); sizeDots(); return; }
    const from = view.slice(), t0 = performance.now(), dur = 420;
    const tick = now => {
      const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      view = from.map((v, i) => v + (target[i] - v) * e);
      svg.setAttribute('viewBox', view.map(v => v.toFixed(1)).join(' '));
      sizeDots();
      if (k < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  function countyBox(name) {
    const c = countyShapes[name];
    if (!c) return null;
    const [x0, y0, x1, y1] = c.box;
    const pad = Math.max((x1 - x0), (y1 - y0)) * 0.25 + 12;
    let w = (x1 - x0) + pad * 2, h = (y1 - y0) + pad * 2;
    const ar = geo.width / geo.height;
    if (w / h < ar) w = h * ar; else h = w / ar;
    return [(x0 + x1) / 2 - w / 2, (y0 + y1) / 2 - h / 2, w, h];
  }

  function drawMap(g) {
    geo = g;
    const p = g.proj;
    const project = (lon, lat) => [p.ox + (lon - p.lon0) * p.k * p.s, p.oy + (p.lat1 - lat) * p.s];
    svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${g.width} ${g.height}`);
    svg.setAttribute('class', 'ohio-svg');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Map of Ohio showing dispensary locations. The list below has the same locations in text.');

    const add = (parent, d, cls) => {
      const el = document.createElementNS(NS, 'path');
      el.setAttribute('d', d); el.setAttribute('class', cls);
      parent.appendChild(el); return el;
    };
    add(svg, g.state, 'ohio-fill');
    const cg = document.createElementNS(NS, 'g');
    g.counties.forEach(c => { countyShapes[c.n] = { el: add(cg, c.d, 'ohio-county'), box: c.b }; });
    svg.appendChild(cg);
    add(svg, g.state, 'ohio-outline');

    const layer = document.createElementNS(NS, 'g');
    layer.setAttribute('class', 'dot-layer');
    const raw = rows.map(x => (x.lat == null || x.lon == null) ? null : project(x.lon, x.lat));
    spread(raw).forEach((pt, i) => {
      if (!pt) { dots.push(null); return; }
      const c = document.createElementNS(NS, 'circle');
      c.setAttribute('cx', pt[0].toFixed(1)); c.setAttribute('cy', pt[1].toFixed(1));
      c.setAttribute('r', String(BASE_R)); c.setAttribute('class', 'map-dot');
      c.dataset.i = String(i);
      layer.appendChild(c); dots.push(c);
    });
    svg.appendChild(layer);

    // Click anywhere: pick the closest visible dot, so tight clusters stay usable.
    svg.addEventListener('click', e => {
      const ctm = svg.getScreenCTM();
      if (!ctm) return;
      const pt = new DOMPoint(e.clientX, e.clientY).matrixTransform(ctm.inverse());
      // Tolerance in screen pixels, converted to user units at the current zoom.
      const perUnit = svg.getBoundingClientRect().width / view[2];
      let best = -1, bestD = 34 / (perUnit || 1);
      dots.forEach((d, i) => {
        if (!d || d.classList.contains('is-dim')) return;
        const dist = Math.hypot(+d.getAttribute('cx') - pt.x, +d.getAttribute('cy') - pt.y);
        if (dist < bestD) { bestD = dist; best = i; }
      });
      if (best > -1) select(best);
    });
    $('ohio-map').replaceChildren(svg);
    view = [0, 0, g.width, g.height];
  }

  function select(i) {
    if (active > -1 && dots[active]) dots[active].classList.remove('is-active');
    active = i;
    const x = rows[i];
    if (dots[i]) dots[i].classList.add('is-active');
    sizeDots();
    $('map-panel').innerHTML =
      '<div class="panel-card"><h2>' + esc(x.name) + '</h2>' +
      '<p class="coverage">' + esc(place(x)) + '</p>' +
      (x.phone ? '<p>Snapshot phone: <a href="tel:' + esc(x.phone.replace(/[^+\d]/g, '')) + '">' + esc(x.phone) + '</a></p>' : '') +
      (x.lic ? '<p class="result-meta">License record: ' + esc(x.lic) + '</p>' : '') +
      '<a class="button dark" href="' + DCC + '" target="_blank" rel="noopener">Verify with Ohio DCC ↗</a></div>';
  }

  function clearPanel() {
    if (active > -1 && dots[active]) dots[active].classList.remove('is-active');
    active = -1; sizeDots();
    $('map-panel').innerHTML = '<div class="panel-card panel-hint"><h2>Pick a spot</h2>' +
      '<p>Tap anywhere on the map to see the closest location, with its address, phone and license record.</p></div>';
  }

  function card(x) {
    return '<article class="listing-card"><div class="listing-top"><h2>' + esc(x.name) + '</h2>' +
      '<span class="tag">' + esc(x.kind || 'Ohio location') + '</span></div>' +
      '<p class="coverage">' + esc(place(x)) + '</p>' +
      (x.phone ? '<p>Snapshot phone: <a href="tel:' + esc(x.phone.replace(/[^+\d]/g, '')) + '">' + esc(x.phone) + '</a></p>' : '') +
      '<div class="listing-actions"><a href="' + DCC + '" target="_blank" rel="noopener">Verify with Ohio DCC ↗</a></div>' +
      '<div class="listing-foot"><span>Map snapshot: ' + esc(x.seen || 'date not recorded') + '</span>' +
      (x.lic ? '<span>License record: ' + esc(x.lic) + '</span>' : '') +
      (x.src ? '<span><a href="' + esc(x.src) + '" target="_blank" rel="noopener">Source ↗</a></span>' : '') +
      '</div></article>';
  }

  function update(zoomTo) {
    const q = $('search').value.toLowerCase().trim();
    const city = $('city').value, county = $('county').value;
    const hits = [];
    rows.forEach((x, i) => {
      const ok = (!city || x.city === city) && (!county || x.county === county) &&
        (!q || [x.name, x.city, x.county, x.address, x.zip].join(' ').toLowerCase().includes(q));
      if (ok) hits.push(i);
      if (dots[i]) dots[i].classList.toggle('is-dim', !ok);
    });
    Object.entries(countyShapes).forEach(([n, c]) => c.el.classList.toggle('is-on', n === county));
    const mapped = hits.filter(i => dots[i]).length;
    $('result-count').textContent = hits.length + ' shown · ' + rows.length + ' Ohio location records · ' + mapped + ' on the map';
    $('results').innerHTML = hits.length
      ? hits.slice(0, 100).map(i => card(rows[i])).join('')
      : '<div class="empty-state">No locations match. Try a nearby city or clear the filters.</div>';
    if (zoomTo !== false) setView(county ? countyBox(county) : null, true);
    if (active > -1 && !hits.includes(active)) clearPanel();
  }

  const fill = (el, label, values) =>
    el.innerHTML = '<option value="">' + label + '</option>' + values.map(v => '<option>' + esc(v) + '</option>').join('');

  Promise.all([
    fetch('data/public-locations.json').then(r => r.json()),
    fetch('data/ohio-map.json').then(r => r.json())
  ]).then(([data, g]) => {
    rows = (data.locations || []).map(norm).sort((a, b) => a.name.localeCompare(b.name));
    drawMap(g);
    fill($('city'), 'All cities', [...new Set(rows.map(x => x.city).filter(Boolean))].sort());
    fill($('county'), 'All counties', [...new Set(rows.map(x => x.county).filter(Boolean))].sort());
    $('search').addEventListener('input', () => update(false));
    $('city').addEventListener('change', () => update(false));
    $('county').addEventListener('change', () => update(true));
    $('map-reset').addEventListener('click', () => {
      $('search').value = ''; $('city').value = ''; $('county').value = '';
      clearPanel(); update(true);
    });
    update(false);
  }).catch(() => {
    $('results').innerHTML = '<div class="empty-state">The location list did not load. Try refreshing this page.</div>';
    $('ohio-map').innerHTML = '<p class="empty-state">The map did not load. The list below still works.</p>';
  });
})();
