#!/usr/bin/env python3
"""Build news.html, the "Ohio news and key dates" page, and the "Coming up" panel on index.html.

Usage: python3 scripts/build_key_dates.py [--today YYYY-MM-DD]

Reads data/ohio-key-dates.json (deadlines, effective dates, comment periods, hearings,
record-sealing clinics and news, each with its source page and the date it was checked)
and data/ohio-events.json (events, already on events.html). Dates that have passed drop
off; news stays listed for 60 days. The refresh workflow runs this every six hours, so
the page always leads with what is coming up next.

The page borrows events.html's head, header and footer so it matches the rest of the site,
including the visit counter and the skip link. Owner direction, November 25, 2026: give
people Ohio news and the dates that matter, soonest first, with pictures.
"""
import argparse, json, re
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
SITE = 'https://ohioweed.org'
NEWS_DAYS = 60
START, END = '<!--key-dates-->', '<!--/key-dates-->'

KINDS = {
    # label, icon path (24x24, stroke), accent
    'deadline': ('Deadline', '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>', '#9a3d12'),
    'effective': ('Law takes effect', '<path d="M5 4h14v16H5z"/><path d="M9 9h6M9 13h6M9 17h3"/>', '#173e34'),
    'comment': ('Public comment', '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9h8M8 12h5"/>', '#5b3f8c'),
    'hearing': ('Hearing or vote', '<path d="M3 20h18M5 20V10m4 10V10m6 10V10m4 10V10M3 10l9-6 9 6z"/>', '#1f4f7a'),
    'clinic': ('Record-sealing help', '<path d="M12 3v18M5 7h14M5 7l-3 7h6zm14 0l-3 7h6z"/>', '#7a5a00'),
    'event': ('Event', '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4m8-4v4"/>', '#255a4a'),
    'news': ('News', '<path d="M4 5h13v14H6a2 2 0 0 1-2-2z"/><path d="M17 8h3v9a2 2 0 0 1-2 2M8 9h5M8 13h5"/>', '#4a4f55'),
}


def icon(kind):
    _, path, _ = KINDS[kind]
    return (f'<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{path}</svg>')


def parse(d):
    return datetime.strptime(d, '%Y-%m-%d').date()


def long_date(d):
    return f'{d:%B} {d.day}, {d.year}'


def when_text(d, end, today):
    days = (d - today).days
    if d <= today <= (end or d):
        return 'Happening now' if end and end != d else 'Today'
    if days == 1:
        return 'Tomorrow'
    if days < 0:
        n = -days
        return f'{n} day{"s" if n != 1 else ""} ago'
    if days <= 60:
        return f'In {days} days'
    months = round(days / 30.4)
    return f'In about {months} months'


def load(today):
    raw = json.loads((REPO / 'data/ohio-key-dates.json').read_text(encoding='utf-8'))
    items = []
    for r in raw['items']:
        if r['kind'] not in KINDS:
            raise SystemExit(f"Unknown kind {r['kind']!r} in data/ohio-key-dates.json")
        for k in ('date', 'title', 'what_it_means', 'source_url', 'source_name', 'checked'):
            if not r.get(k):
                raise SystemExit(f"{r.get('title', r)!r} is missing {k}")
        if not r['source_url'].startswith('https://'):
            raise SystemExit(f"{r['title']!r}: source must be an https page")
        items.append(dict(r, d=parse(r['date']), e=parse(r['end']) if r.get('end') else None))
    events = json.loads((REPO / 'data/ohio-events.json').read_text(encoding='utf-8'))
    for ev in events:
        items.append({'kind': 'event', 'title': ev['name'].replace(' — ', ': '), 'd': parse(ev['start']),
                      'e': parse(ev['end']) if ev.get('end') and ev['end'] != ev['start'] else None,
                      'what_it_means': 'Registration, tickets and any changes are on the organizer’s page.',
                      'who': 'Event organizer', 'source_url': ev['url'], 'source_name': 'Organizer page',
                      'checked': raw.get('events_checked', raw['updated'])})
    upcoming = sorted((i for i in items if i['kind'] != 'news' and (i['e'] or i['d']) >= today), key=lambda i: i['d'])
    news = sorted((i for i in items if i['kind'] == 'news' and i['d'] >= today - timedelta(days=NEWS_DAYS)),
                  key=lambda i: i['d'], reverse=True)
    return raw, upcoming, news


def tile(d):
    return (f'<div class="kd-tile" aria-hidden="true"><small>{d:%b}</small><strong>{d.day}</strong>'
            f'<small>{d.year}</small></div>')


def card(i, today, level='h3'):
    label, _, accent = KINDS[i['kind']]
    span = long_date(i['d']) + (f' to {long_date(i["e"])}' if i['e'] else '')
    who = f' · {escape(i["who"])}' if i.get('who') else ''
    return (f'<li class="kd-item" style="--kd:{accent}">{tile(i["d"])}<div class="kd-body">'
            f'<p class="kd-meta"><span class="kd-kind">{icon(i["kind"])}{label}</span>'
            f'<span class="kd-when">{when_text(i["d"], i["e"], today)}</span></p>'
            f'<{level}>{escape(i["title"])}</{level}>'
            f'<p class="kd-date"><time datetime="{i["d"].isoformat()}">{span}</time>{who}</p>'
            f'<p>{escape(i["what_it_means"])}</p>'
            f'<p class="kd-src"><a href="{escape(i["source_url"])}" target="_blank" rel="noopener">'
            f'{escape(i["source_name"])} ↗</a> <span>Checked {long_date(parse(i["checked"]))}</span></p>'
            f'</div></li>')


CSS = """<style>/* key-dates */
.kd-wrap{max-width:980px}
.kd-next{display:flex;gap:22px;align-items:flex-start;background:var(--paper,#fffdf7);border:2px solid var(--pine,#173e34);border-radius:22px;padding:24px;margin:0 0 30px}
.kd-next h2{margin:6px 0 8px;font-size:clamp(1.4rem,3vw,2rem);letter-spacing:-.03em}
.kd-next .kd-tile{width:92px;height:104px}.kd-next .kd-tile strong{font-size:2.3rem}
.kd-tile{width:68px;height:80px;flex:0 0 auto;background:var(--lime,#d7f080);border-radius:14px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--pine,#173e34);font-weight:900;line-height:1.1}
.kd-tile small{text-transform:uppercase;letter-spacing:.08em;font-size:.68rem}.kd-tile strong{font-size:1.6rem}
.kd-months{list-style:none;padding:0;margin:0 0 34px;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,130px),1fr));gap:10px}
.kd-months li{border:1px solid var(--line,#d9ded3);border-top:5px solid var(--pine,#173e34);border-radius:12px;padding:12px;background:#fff}
.kd-months li.kd-empty{border-top-color:#c9cfc6;color:#5c6862}
.kd-months strong{display:block;font-size:1rem}.kd-months span{font-size:.9rem}
.kd-dots{display:flex;gap:4px;margin-top:8px;flex-wrap:wrap}.kd-dots i{width:12px;height:12px;border-radius:50%;background:var(--kd,#173e34)}
.kd-list{list-style:none;padding:0;margin:0 0 32px;display:grid;gap:14px}
.kd-item{display:flex;gap:18px;background:var(--paper,#fffdf7);border:1px solid var(--line,#d9ded3);border-left:6px solid var(--kd);border-radius:18px;padding:18px}
.kd-body{min-width:0}.kd-body h2,.kd-body h3{margin:4px 0 6px;font-size:1.2rem;letter-spacing:-.02em}
.kd-body p{margin:0 0 8px}
.kd-meta{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;font-size:.88rem;font-weight:700}
.kd-kind{display:inline-flex;gap:6px;align-items:center;color:var(--kd)}
.kd-when{background:#eef2ea;color:#173e34;border-radius:999px;padding:2px 10px}
.kd-date{color:#3f4a45;font-size:.93rem}
.kd-src{font-size:.9rem}.kd-src span{color:#5c6862;margin-left:6px}
.kd-month-h{margin:28px 0 12px;font-size:1.35rem}
.kd-teaser .kd-list{margin-bottom:14px}
@media(max-width:560px){.kd-item,.kd-next{flex-direction:column}}
@media (forced-colors:active){.kd-item,.kd-next,.kd-months li{border-color:CanvasText}.kd-dots i{forced-color-adjust:none;background:CanvasText}}
</style>"""


def page(raw, upcoming, news, today):
    tpl = (REPO / 'events.html').read_text(encoding='utf-8')
    head, rest = tpl.split('<main id="main-content">', 1)
    foot = '</main>' + rest.split('</main>', 1)[1]
    title = 'Ohio Cannabis News and Key Dates | OhioWeed'
    desc = ('What is coming up for Ohio cannabis: deadlines, law changes, public comment periods, '
            'hearings, record-sealing clinics and events, soonest first, each with its official source.')
    head = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', head, count=1)
    head = re.sub(r'(<meta name="description" content=")[^"]*', lambda m: m.group(1) + desc, head, count=1)
    head = re.sub(r'(<meta property="og:title" content=")[^"]*', lambda m: m.group(1) + title, head)
    head = re.sub(r'(<meta property="og:description" content=")[^"]*', lambda m: m.group(1) + desc, head)
    head = head.replace(f'{SITE}/events.html', f'{SITE}/news.html').replace('"name":"Ohio events"', '"name":"Ohio news and key dates"')
    foot = foot.replace('<script src="assets/events.js" defer></script>', '')
    head = head.replace('</head>', CSS + '</head>', 1)

    parts = [f'<section class="page-hero"><div class="wrap"><div class="breadcrumbs"><a href="index.html">Home</a> / News and key dates</div>'
             f'<div class="eyebrow">Updated {long_date(today)}</div><h1>What’s coming up in Ohio.</h1>'
             '<p>Deadlines, law changes, chances to comment, hearings, record-sealing clinics and events, soonest first. '
             'Each one links to the official or organizer page it came from, with the date we checked it.</p></div></section>',
             '<section class="section"><div class="wrap kd-wrap">']
    if upcoming:
        nxt = upcoming[0]
        label, _, accent = KINDS[nxt['kind']]
        parts.append(f'<div class="kd-next" style="--kd:{accent}">{tile(nxt["d"])}<div class="kd-body">'
                     f'<p class="kd-meta"><span class="kd-kind">{icon(nxt["kind"])}Next up: {label}</span>'
                     f'<span class="kd-when">{when_text(nxt["d"], nxt["e"], today)}</span></p>'
                     f'<h2>{escape(nxt["title"])}</h2><p class="kd-date"><time datetime="{nxt["d"].isoformat()}">{long_date(nxt["d"])}</time></p>'
                     f'<p>{escape(nxt["what_it_means"])}</p><p class="kd-src"><a href="{escape(nxt["source_url"])}" target="_blank" rel="noopener">'
                     f'{escape(nxt["source_name"])} ↗</a></p></div></div>')
        # the year ahead at a glance: one tile per month that has dates
        horizon = date(today.year + 1, today.month, 1)
        months = sorted({(i['d'].year, i['d'].month) for i in upcoming if i['d'] < horizon})
        parts.append('<h2 class="kd-month-h" id="glance">The year ahead at a glance</h2><ol class="kd-months">')
        for (y, m) in months:
            hits = [i for i in upcoming if (i['d'].year, i['d'].month) == (y, m)]
            n = len(hits)
            kinds = ', '.join(dict.fromkeys(KINDS[i['kind']][0].lower() for i in hits))
            dots = ''.join(f'<i style="--kd:{KINDS[i["kind"]][2]}"></i>' for i in hits)
            parts.append(f'<li><strong><a href="#m-{y}-{m:02d}">{date(y, m, 1):%B %Y}</a></strong>'
                         f'<span>{n} date{"s" if n != 1 else ""}: {kinds}</span>'
                         f'<span class="kd-dots" aria-hidden="true">{dots}</span></li>')
        parts.append('</ol>')
        parts.append('<h2 class="kd-month-h">Coming up, soonest first</h2>')
        cur = None
        for i in upcoming:
            key = (i['d'].year, i['d'].month)
            if key != cur:
                if cur:
                    parts.append('</ol>')
                parts.append(f'<h3 class="kd-month-h" id="m-{key[0]}-{key[1]:02d}">{i["d"]:%B %Y}</h3><ol class="kd-list">')
                cur = key
            parts.append(card(i, today, 'h4'))
        parts.append('</ol>')
    else:
        parts.append('<div class="empty-state">No upcoming dates are listed right now.</div>')
    if news:
        parts.append(f'<h2 class="kd-month-h" id="news">Recent Ohio cannabis news</h2><ol class="kd-list">')
        parts.extend(card(i, today) for i in news)
        parts.append('</ol>')
    parts.append('<div class="notice"><strong>Check before you act.</strong> Dates can move. Each item links to the page it came from; '
                 'that page is the one to trust. Know of a date Ohioans need? '
                 '<a href="https://github.com/travisvought-byte/OhioWeed/issues/new">Suggest it</a> with a link to the official page.</div>')
    parts.append('</div></section>')
    return head + '<main id="main-content">' + ''.join(parts) + foot


def teaser(upcoming, today):
    nxt = upcoming[:3]
    if not nxt:
        return ''
    return (f'{START}<section class="section kd-teaser" aria-labelledby="kd-teaser-h"><div class="wrap">'
            '<div class="section-head"><div><div class="eyebrow">Ohio news and key dates</div>'
            '<h2 id="kd-teaser-h">Coming up in Ohio.</h2></div>'
            '<p>The next dates that matter, with the official source for each.</p></div>'
            '<ol class="kd-list">' + ''.join(card(i, today) for i in nxt) + '</ol>'
            '<p><a class="button" href="news.html">See every date and the latest news ↗</a></p></div></section>' + END)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--today', help='YYYY-MM-DD; defaults to today in Ohio')
    args = ap.parse_args()
    today = parse(args.today) if args.today else datetime.now(ZoneInfo('America/New_York')).date()
    raw, upcoming, news = load(today)
    (REPO / 'news.html').write_text(page(raw, upcoming, news, today), encoding='utf-8')
    idx = REPO / 'index.html'
    html = idx.read_text(encoding='utf-8')
    block = teaser(upcoming, today)
    if START in html:
        html = re.sub(re.escape(START) + '.*?' + re.escape(END), lambda m: block, html, flags=re.S)
    else:
        anchor = html.index('<div class="eyebrow">Start where you are</div>')
        sec = html.rindex('<section', 0, anchor)
        html = html[:sec] + block + html[sec:]
    if '/* key-dates */' not in html:
        html = html.replace('</head>', CSS + '</head>', 1)
    idx.write_text(html, encoding='utf-8')
    print(f'news.html: {len(upcoming)} upcoming, {len(news)} news; next: '
          f'{upcoming[0]["title"] + " (" + upcoming[0]["d"].isoformat() + ")" if upcoming else "none"}')


if __name__ == '__main__':
    main()
