#!/usr/bin/env python3
"""Write a plain list of Ohio dispensary location records into dispensaries.html.

The map and search on that page are drawn by JavaScript. This list is ordinary HTML,
grouped by county and city, so people without JavaScript and search engines can read
every location record too. It is rebuilt from data/public-locations.json each time,
between the markers <!-- location-list:start --> and <!-- location-list:end -->.
Idempotent: running it twice gives the same page.
"""
import html, json, re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAGE = REPO / 'dispensaries.html'
DATA = REPO / 'data' / 'public-locations.json'
START, END = '<!-- location-list:start -->', '<!-- location-list:end -->'
# The list goes right after the source note under the map.
ANCHOR = 'Listings are factual records, not endorsements or paid placements.</p>'


def build_block(locations):
    by_county = defaultdict(lambda: defaultdict(list))
    for loc in locations:
        if loc.get('state') != 'OH':
            continue
        county = (loc.get('county') or 'County not listed').strip()
        city = (loc.get('city') or 'City not listed').strip()
        by_county[county][city].append(loc)
    esc = html.escape
    parts = [START,
             '<section aria-labelledby="by-county" style="margin-top:34px">',
             '<h2 id="by-county" style="font-size:1.6rem;letter-spacing:-.04em;margin:0 0 6px">Ohio dispensary locations by county and city</h2>',
             '<p class="result-meta">The same records as the map, from the Ohio government map snapshot. '
             'Confirm current license status, hours and medical or adult-use service with the Division of Cannabis Control before you go.</p>']
    for county in sorted(by_county):
        cities = by_county[county]
        count = sum(len(v) for v in cities.values())
        parts.append(f'<details><summary><strong>{esc(county)} County</strong> ({count})</summary>')
        for city in sorted(cities):
            parts.append(f'<h3 style="font-size:1rem;margin:14px 0 4px">{esc(city)}</h3><ul style="margin:0 0 6px;padding-left:20px">')
            for loc in sorted(cities[city], key=lambda l: (l.get('name') or '').lower()):
                addr = ', '.join(x for x in [loc.get('address'), loc.get('city'), ('OH ' + loc['postal_code']) if loc.get('postal_code') else 'OH'] if x)
                phone = loc.get('snapshot_phone')
                line = f'<strong>{esc(loc.get("name") or "Unnamed location")}</strong>, {esc(addr)}'
                if phone:
                    line += f', {esc(phone)}'
                parts.append(f'<li>{line}</li>')
            parts.append('</ul>')
        parts.append('</details>')
    parts += ['</section>', END]
    return ''.join(parts)


def main():
    page = PAGE.read_text()
    data = json.loads(DATA.read_text())
    block = build_block(data['locations'] if isinstance(data, dict) else data)
    if START in page:
        page = re.sub(re.escape(START) + '.*?' + re.escape(END), lambda m: block, page, count=1, flags=re.S)
    elif ANCHOR in page:
        page = page.replace(ANCHOR, ANCHOR + block, 1)
    else:
        raise SystemExit('dispensaries.html: could not find where to put the location list')
    PAGE.write_text(page)
    print('Wrote the location list into dispensaries.html')


if __name__ == '__main__':
    main()
