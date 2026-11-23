#!/usr/bin/env python3
"""Publish the Ohio pages built by ohio-cannabis-directory onto ohioweed.org.

Usage: python3 scripts/mirror_directory.py <path-to-ohio-cannabis-directory> [--out .]

What it does:
1. Copies the directory repo to a scratch folder (the source is never changed).
2. Keeps only Ohio records: public organizations whose published service area
   names Ohio, the owners of Ohio dispensary locations, their Ohio locations and
   services, and the evidence they cite. Other states are removed from the copy only.
3. Builds the directory pages with SITE_ORIGIN=https://ohioweed.org.
4. Copies the Ohio pages, assets, data and exports into this repo.
   OhioWeed's own home, directory, dispensaries, events and rules pages are not touched.
5. Removes the directory's click-tracking script (OhioWeed counts page visits with its
   own counter, added in step 7, so nothing is counted twice) and points
   Pennsylvania and multistate links at the-reefer.com, the national site where those pages live
   (weed.vethomeguard.org is retired and only forwards; owner direction, November 16, 2026).
6. Checks that every local link and asset resolves, then rewrites sitemap.xml.
7. Adds the page-visit counter to every page (scripts/add_counter.py).
"""
import argparse, csv, json, re, shutil, subprocess, sys, tempfile
from html import escape as html_escape
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
from ohio_filter import filter_directory  # noqa: E402
from add_counter import add_counter  # noqa: E402

PAGES = ['advocacy', 'ancestry', 'assessment', 'buyer-guide', 'compare', 'expungement', 'intake',
         'knowledge', 'lawmakers', 'locations', 'november-campaign', 'relationships', 'resources',
         'seeds', 'work-with-travis']
DATA_FILES = ['directory.json', 'knowledge.json', 'legislators.json', 'public-locations.json',
              'public-organizations.json', 'public-strains.json', 'state-comparison.json']
# Copied when the directory has them, so a refresh never fails while a new file is
# still in review there. compare.html loads public-permissions.json for its state switcher.
OPTIONAL_DATA_FILES = ['public-permissions.json']
ROOT_FILES = ['ohio-cannabis-directory.csv', 'b2b-relationships.csv', 'seed-suppliers.json']
FILTERED_CSVS = {'ohio-cannabis-directory.csv', 'b2b-relationships.csv'}
NOT_MIRRORED = {'state.html', 'pennsylvania-directory.html', 'pennsylvania-advocacy.html', 'directory.html', 'index.html'}
WEED = 'https://the-reefer.com/'
SITE = 'https://ohioweed.org'
# Pages written in this repo rather than mirrored from the directory. They are
# never overwritten by a refresh, and they belong in the sitemap alongside the
# mirrored ones.
OWN_PAGES = {'index.html', 'directory.html', 'dispensaries.html', 'events.html', 'rules.html', 'medical.html',
             'mjbizcon.html', 'veteran-grow.html', 'find.html', 'join.html'}


def ohio_org_ids(src: Path) -> set:
    """Ohio organizations: public records whose published service area names Ohio or OH."""
    orgs = json.loads((src / 'data/directory.json').read_text(encoding='utf-8'))['organizations']
    ids = set()
    for o in orgs:
        if o.get('scope') != 'public':
            continue
        lr = o.get('legacy_record') or {}
        text = f"{lr.get('Service Area') or ''} {lr.get('Service Area (as published)') or ''}"
        if re.search(r'\bOhio\b|\bOH\b', text):
            ids.add(o['id'])
    return ids


def build(src: Path, ids: set) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix='ohio-build-'))
    work = tmp / 'directory'
    shutil.copytree(src, work, ignore=shutil.ignore_patterns('.git', 'node_modules', '__pycache__'))
    ids_file = tmp / 'ohio-ids.json'
    ids_file.write_text(json.dumps([{'id': i} for i in sorted(ids)]), encoding='utf-8')
    filter_directory(work, ids_file)
    # RL_invariant makes reportlab write fixed dates and file IDs, so the PDFs come out
    # byte-identical from one run to the next and the refresh only commits real changes.
    env = {**__import__('os').environ, 'SITE_ORIGIN': SITE, 'RL_invariant': '1'}
    for script in sorted(work.glob('build_*.py')):
        r = subprocess.run([sys.executable, script.name], cwd=work, env=env, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise SystemExit(f'{script.name} failed:\n{r.stderr[-800:]}')
    return work


NOTE_OLD = 'Your state/topic choices are not included in analytics events.'
NOTE_NEW = 'Your state/topic choices are not stored or sent anywhere.'


# The mirrored pages wear OhioWeed's own header, page hero and footer, and take its colors
# and type from assets/ow-theme.css (loaded after each page's own styles), so they read as
# part of this site rather than a separate one. The directory's own brand line and page
# menu (VHG logo, "Ohio Cannabis Directory", a Pennsylvania button) are removed here.
# Owner direction, November 20, 2026: make OhioWeed better visually.
OW_HEADER = (
    '<header class="ow-header"><div class="ow-nav">'
    '<a class="ow-brand" href="index.html"><img src="favicon.svg" alt="" width="36" height="36">'
    '<span>OhioWeed<small>The Ohio cannabis guide</small></span></a>'
    '<button class="ow-menu" type="button" aria-expanded="false" aria-controls="ow-links">Menu</button>'
    '<nav id="ow-links" class="ow-links" aria-label="Main navigation">'
    '<a href="dispensaries.html">Dispensaries</a><a href="events.html">Events</a>'
    '<a href="find.html?for=grow">Grow</a><a href="find.html?for=law">Law &amp; rights</a>'
    '<a href="find.html?for=business">Business</a><a href="medical.html">Medical card</a>'
    '<a href="https://the-reefer.com/">All states</a></nav>'
    '<form class="ow-search" action="find.html" method="get" role="search">'
    '<label class="ow-sr" for="ow-q">Search the guide</label>'
    '<input id="ow-q" name="q" type="search" placeholder="Search the guide" autocomplete="off">'
    '<button type="submit" aria-label="Search"><span aria-hidden="true">→</span></button></form>'
    '</div></header>'
    '<script>(()=>{const b=document.querySelector(".ow-menu"),n=document.getElementById("ow-links");'
    'if(b&&n)b.addEventListener("click",()=>{const o=n.classList.toggle("open");b.setAttribute("aria-expanded",o)})})();</script>'
)
OW_FOOTER = (
    '<footer class="ow-footer"><div class="ow-footer-wrap"><div class="ow-footer-grid"><div>'
    '<a class="ow-brand" href="index.html"><img src="favicon.svg" alt="" width="36" height="36">'
    '<span>OhioWeed<small>The Ohio cannabis guide</small></span></a>'
    '<p>An independent, source-linked guide to Ohio cannabis organizations, licensed locations, public resources, '
    'events and state rules. It is not an endorsement, legal or medical advice, or a substitute for current official information.</p></div>'
    '<nav class="ow-footer-links" aria-label="Footer">'
    '<a href="find.html">Find what you need</a><a href="directory.html">Business directory</a>'
    '<a href="dispensaries.html">Dispensary lookup</a><a href="events.html">Ohio events</a>'
    '<a href="rules.html">Rules and resources</a><a href="medical.html">Medical card</a>'
    '<a href="knowledge.html">Learn</a><a href="buyer-guide.html">Shop smart</a><a href="ancestry.html">Strains</a>'
    '<a href="seeds.html">Seeds &amp; growing</a><a href="expungement.html">Record clearing</a>'
    '<a href="advocacy.html">Advocacy</a><a href="lawmakers.html">Your lawmakers</a><a href="compare.html">Compare states</a>'
    '<a href="relationships.html">Who works with whom</a><a href="assessment.html">Business self-check</a>'
    '<a href="veteran-grow.html">Veteran growers</a><a href="join.html">Event email</a>'
    '<a href="https://github.com/travisvought-byte/OhioWeed/issues/new">Suggest a correction</a></nav></div>'
    '<div class="ow-copy">© 2026 OhioWeed.org · Independent guide · Data attribution: “Ohio Cannabis Ecosystem Directory, '
    'compiled by Travis Vought.” Licensed data reused under CC BY 4.0. <a href="SITE_DATA.md">Source and reuse notes</a></div>'
    '</div></footer>'
)
OW_THEME = '<link rel="stylesheet" href="assets/ow-theme.css">'
# The directory's own brand line, page menu and the little script that closes that menu.
DIRECTORY_CHROME = re.compile(
    r'<a class="vhg-brand"[^>]*>.*?</a>\s*'
    r'(?:<nav class="knowledge-links site-nav"[^>]*>.*?</details></nav>\s*'
    r'(?:<script>\(\(\)=>\{const close=.*?</script>\s*)?)?', re.S)
BACK_LINK = re.compile(r'\s*(?:<p(?: class="back")?>\s*<a href="index\.html">←[^<]*</a>(?:\s*·\s*<a [^>]*>[^<]*</a>)*\s*</p>|<a href="index\.html">←[^<]*</a>)')
LEAD = re.compile(r'\s*<p(?: class="(?:lead|sub|buyer-intro|stat-line)")?>(?:(?!</p>).)*</p>', re.S)


def hero(body: str) -> str:
    """Move the page's title, its eyebrow line and its opening sentence into an OhioWeed hero.

    Only plain cases move: an <h1> with, just before it, an optional eyebrow paragraph (review
    date or topic tag) and, just after it, an optional plain or lead paragraph. Anything else
    stays where the page put it, so a page with unusual markup keeps its title in place."""
    m = re.search(r'<main\b[^>]*>', body)
    if not m:
        return body
    h1 = re.compile(r'<h1\b[^>]*>.*?</h1>', re.S).search(body, m.end())
    if not h1:
        return body
    start, end = h1.start(), h1.end()
    before = body[m.end():start]
    eyebrow = ''
    tail = re.search(r'(<p class="(?:review|tag|eyebrow)"[^>]*>(?:(?!</p>).)*</p>)\s*$', before, re.S)
    if tail:
        eyebrow = tail.group(1)
        start = m.end() + tail.start()
    lead = ''
    after = LEAD.match(body, end)
    if after and len(re.sub(r'<[^>]+>', '', after.group(0)).strip()) <= 320 and '<form' not in after.group(0):
        lead = after.group(0).strip()
        end = after.end()
    crumbs = '<p class="ow-crumbs"><a href="index.html">Home</a></p>'
    eyebrow_html = re.sub(r'^<p class="[^"]*"', '<p class="ow-eyebrow"', eyebrow) if eyebrow else ''
    lead_html = re.sub(r'^<p class="[^"]*"', '<p', lead) if lead else ''
    section = (f'<section class="ow-hero"><div class="ow-hero-in">{crumbs}{eyebrow_html}'
               f'{body[h1.start():h1.end()]}{lead_html}</div></section>')
    body = body[:start] + body[end:]
    return body[:m.start()] + section + body[m.start():]


# The directory's accent colors, swapped for OhioWeed's inside each mirrored page's own styles:
# its reds and its blue become OhioWeed's greens, its grey background OhioWeed's cream.
COLOR_SWAP = {'#a90000': '#255a4a', '#ba0c2f': '#255a4a', '#8c0924': '#173e34', '#9d0927': '#173e34',
              '#70071c': '#173e34', '#215b76': '#173e34', '#f5f5f3': '#f5f2e9'}
COLOR_RE = re.compile('|'.join(COLOR_SWAP), re.I)


def recolor(text: str) -> str:
    return re.sub(r'(<style[^>]*>)(.*?)(</style>)',
                  lambda m: m.group(1) + COLOR_RE.sub(lambda c: COLOR_SWAP[c.group(0).lower()], m.group(2)) + m.group(3),
                  text, flags=re.S)


def dress_page(text: str) -> str:
    """OhioWeed header, hero and footer for a mirrored page, in place of the directory's own top."""
    text = recolor(text)
    text = DIRECTORY_CHROME.sub('', text, count=1)
    text = BACK_LINK.sub('', text, count=1)
    text = hero(text)
    text = text.replace('</head>', OW_THEME + '</head>', 1)
    text = re.sub(r'(<body[^>]*>)', lambda m: m.group(1) + OW_HEADER, text, count=1)
    return text.replace('</body>', OW_FOOTER + '</body>', 1)


HEAD_ICON = '<link rel="icon" href="favicon.svg"><link rel="apple-touch-icon" href="favicon.svg">'


CARD = SITE + '/assets/og-card.png'
# Pages that share their own picture instead of the site card: (image, width, height).
CARDS = {'advocacy': (SITE + '/assets/ohio-what-changed.jpg', 1536, 1024)}

# Each mirrored page now carries its own description from the directory build
# (ohio-cannabis-directory data/landing-pages.json, November 23, 2026), so nothing is overridden here.
# An entry added below would replace that page's description and share-card text.
DESCRIPTIONS = {}


def brand_page(text: str, name: str) -> str:
    """Give a mirrored page OhioWeed's icon, tab title, canonical URL, share card, header, hero and footer."""
    text = re.sub(r'(<title>[^<]*?)\s*\|\s*Ohio Cannabis Directory(</title>)', r'\1 | OhioWeed\2', text)
    text = re.sub(r'(<meta property="og:title" content="[^"]*?)\s*\|\s*Ohio Cannabis Directory(")', r'\1 | OhioWeed\2', text)

    desc = DESCRIPTIONS.get(name)
    if desc:
        for attr in ('name="description"', 'property="og:description"'):
            text = re.sub(rf'<meta {re.escape(attr)} content="[^"]*">', f'<meta {attr} content="{desc}">', text)

    url = f'{SITE}/{name}.html'
    title = re.search(r'<title>([^<]*)</title>', text)
    found = re.search(r'<meta name="description" content="([^"]*)">', text)
    head = HEAD_ICON
    if not re.search(r'<link rel="canonical"', text):
        head += f'<link rel="canonical" href="{url}">'
    if not re.search(r'<meta property="og:url"', text):
        head += f'<meta property="og:url" content="{url}">'
    card, card_w, card_h = CARDS.get(name, (CARD, 1200, 630))
    head += (f'<meta property="og:image" content="{card}">'
             f'<meta property="og:image:width" content="{card_w}">'
             f'<meta property="og:image:height" content="{card_h}">'
             '<meta name="twitter:card" content="summary_large_image">'
             f'<meta name="twitter:image" content="{card}">')
    if title:
        head += f'<meta name="twitter:title" content="{html_escape(title.group(1))}">'
    if found:
        head += f'<meta name="twitter:description" content="{found.group(1)}">'

    text = text.replace('<head>', '<head>' + head, 1)
    return dress_page(text)

def clean_page(text: str, name: str) -> str:
    text = re.sub(r'<script\b[^>]*\bsrc="assets/analytics\.js"[^>]*>\s*</script>\s*', '', text)
    text = text.replace(NOTE_OLD, NOTE_NEW)
    def rewrite(m):
        target = m.group(2)
        if target.startswith(('http://', 'https://', '#', 'mailto:', 'tel:')):
            return m.group(0)
        path = target.split('#')[0].split('?')[0]
        if path in {'state.html', 'pennsylvania-directory.html', 'pennsylvania-advocacy.html'}:
            return f'{m.group(1)}="{WEED}{target}"'
        return m.group(0)
    return brand_page(re.sub(r'(href)="([^"]+)"', rewrite, text), name)


def copy_into(work: Path, out: Path, ids: set):
    for name in PAGES:
        page = clean_page((work / f'{name}.html').read_text(encoding='utf-8'), name)
        if 'assets/analytics.js' in page or 'goatcounter' in page:
            raise SystemExit(f'{name}.html still loads analytics')
        (out / f'{name}.html').write_text(page, encoding='utf-8')
    (out / 'assets').mkdir(exist_ok=True)
    for f in (work / 'assets').iterdir():
        if f.is_dir():
            shutil.copytree(f, out / 'assets' / f.name, dirs_exist_ok=True)
        elif f.name not in {'analytics.js', 'pennsylvania-advocacy.js'}:
            shutil.copy2(f, out / 'assets' / f.name)
    (out / 'data/strains').mkdir(parents=True, exist_ok=True)
    for name in DATA_FILES:
        shutil.copy2(work / 'data' / name, out / 'data' / name)
    for name in OPTIONAL_DATA_FILES:
        if (work / 'data' / name).is_file():
            shutil.copy2(work / 'data' / name, out / 'data' / name)
        else:
            print(f'data/{name}: not in the directory yet, skipped')
    for f in (work / 'data/strains').iterdir():
        if f.is_file():
            shutil.copy2(f, out / 'data/strains' / f.name)
    for name in ROOT_FILES:
        if name not in FILTERED_CSVS:
            shutil.copy2(work / name, out / name)
    filter_csvs(work, out, ids)
    write_directory_list(out, ids)


def write_directory_list(out: Path, ohio_ids: set):
    """The searchable list on OhioWeed's directory page, built from the filtered Ohio CSV."""
    with (out / 'ohio-cannabis-directory.csv').open(encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        col = {h: i for i, h in enumerate(header)}
        records = []
        for r in reader:
            if r[col['Record ID']] not in ohio_ids:
                continue
            records.append({
                'id': r[col['Record ID']],
                'name': r[col['Organization / Business Name']],
                'category': r[col['Category']],
                'type': r[col['Type']],
                'person': r[col['Contact Person']],
                'email': r[col['Email']],
                'phone': r[col['Phone']],
                'website': r[col['Website']],
                'sources': [u.strip() for u in r[col['Source(s)']].split(' | ') if u.strip()],
                'coverage': r[col['Service Area']],
                'publishedCoverage': r[col['Service Area (as published)']],
                'reviewed': r[col['Last Reviewed']],
                'verification': r[col['Verification Tier']],
                'capabilities': r[col['Capabilities / Keywords']],
            })
    records.sort(key=lambda o: o['name'].lower())
    (out / 'data/ohio-directory.json').write_text(
        json.dumps(records, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'data/ohio-directory.json: {len(records)} records')


def filter_csvs(work: Path, out: Path, ohio_ids: set):
    """Keep only Ohio rows in the two CSV exports, using the same org set as the JSON."""
    names = {o['name'].strip().lower() for o in json.loads((work / 'data/directory.json').read_text(encoding='utf-8'))['organizations']}

    def write_rows(src: Path, dst: Path, keep):
        with src.open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.reader(f))
        kept = [rows[0]] + [r for r in rows[1:] if keep(r)]
        with dst.open('w', encoding='utf-8-sig', newline='') as f:
            csv.writer(f, lineterminator='\n').writerows(kept)
        print(f'{dst.name}: {len(kept) - 1} of {len(rows) - 1} rows kept')

    write_rows(work / 'ohio-cannabis-directory.csv', out / 'ohio-cannabis-directory.csv',
               lambda r: len(r) > 13 and r[13] in ohio_ids)
    write_rows(work / 'b2b-relationships.csv', out / 'b2b-relationships.csv',
               lambda r: len(r) > 1 and r[0].strip().lower() in names and r[1].strip().lower() in names)


def check_links(out: Path):
    problems = []
    existing = {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()}
    own = existing | OWN_PAGES
    for name in PAGES:
        text = (out / f'{name}.html').read_text(encoding='utf-8')
        for target in re.findall(r'(?:href|src)="([^"]+)"', text):
            if target.startswith(('http://', 'https://', '#', 'mailto:', 'tel:', 'data:', 'javascript:')):
                continue
            path = unquote(target.split('#')[0].split('?')[0])
            if not re.fullmatch(r'[A-Za-z0-9._/-]*', path):
                continue  # inline JavaScript string built in a template, not a link
            if path and path not in own:
                problems.append(f'{name}.html -> {target}')
        if 'weed.vethomeguard.org' in text:
            problems.append(f'{name}.html still links to the retired weed.vethomeguard.org')
    if problems:
        raise SystemExit('Broken or unexpected links:\n' + '\n'.join(sorted(set(problems))[:40]))


def write_sitemap(out: Path):
    pages = sorted(OWN_PAGES | {f'{p}.html' for p in PAGES})
    urls = [f"{SITE}/" if p == 'index.html' else f"{SITE}/{p}" for p in pages]
    body = ''.join(f'  <url><loc>{u}</loc></url>\n' for u in urls)
    (out / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + '</urlset>\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('directory', type=Path)
    ap.add_argument('--out', type=Path, default=REPO)
    args = ap.parse_args()
    src = args.directory.resolve()
    ids = ohio_org_ids(src)
    print(f'Ohio organizations in source: {len(ids)}')
    work = build(src, ids)
    copy_into(work, args.out.resolve(), ids)
    check_links(args.out.resolve())
    write_sitemap(args.out.resolve())
    add_counter(args.out.resolve())
    print(f'Mirrored {len(PAGES)} Ohio pages into {args.out}')


if __name__ == '__main__':
    main()
