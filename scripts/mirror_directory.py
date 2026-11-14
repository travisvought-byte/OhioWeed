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
5. Removes the GoatCounter script (OhioWeed does not track visitors) and points
   Pennsylvania and multistate links at weed.vethomeguard.org, where those pages still live.
6. Checks that every local link and asset resolves, then rewrites sitemap.xml.
"""
import argparse, csv, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
from ohio_filter import filter_directory  # noqa: E402

PAGES = ['advocacy', 'ancestry', 'assessment', 'buyer-guide', 'compare', 'expungement', 'intake',
         'knowledge', 'lawmakers', 'locations', 'november-campaign', 'relationships', 'resources',
         'seeds', 'work-with-travis']
DATA_FILES = ['directory.json', 'knowledge.json', 'legislators.json', 'public-locations.json',
              'public-organizations.json', 'public-strains.json', 'state-comparison.json']
ROOT_FILES = ['ohio-cannabis-directory.csv', 'b2b-relationships.csv', 'seed-suppliers.json']
FILTERED_CSVS = {'ohio-cannabis-directory.csv', 'b2b-relationships.csv'}
NOT_MIRRORED = {'state.html', 'pennsylvania-directory.html', 'pennsylvania-advocacy.html', 'directory.html', 'index.html'}
WEED = 'https://weed.vethomeguard.org/'
SITE = 'https://ohioweed.org'
OWN_PAGES = {'index.html', 'directory.html', 'dispensaries.html', 'events.html', 'rules.html'}


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
    env = {**__import__('os').environ, 'SITE_ORIGIN': SITE}
    for script in sorted(work.glob('build_*.py')):
        r = subprocess.run([sys.executable, script.name], cwd=work, env=env, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise SystemExit(f'{script.name} failed:\n{r.stderr[-800:]}')
    return work


NOTE_OLD = 'Your state/topic choices are not included in analytics events.'
NOTE_NEW = 'Your state/topic choices are not stored or sent anywhere.'


def clean_page(text: str) -> str:
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
    return re.sub(r'(href)="([^"]+)"', rewrite, text)


def copy_into(work: Path, out: Path, ids: set):
    for name in PAGES:
        page = clean_page((work / f'{name}.html').read_text(encoding='utf-8'))
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
            csv.writer(f, lineterminator='\r\n').writerows(kept)
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
        if 'weed.vethomeguard.org' in text and WEED not in text:
            problems.append(f'{name}.html has a weed.vethomeguard.org reference that is not the Pennsylvania link')
    if problems:
        raise SystemExit('Broken or unexpected links:\n' + '\n'.join(sorted(set(problems))[:40]))


def write_sitemap(out: Path):
    pages = sorted(['index.html', 'directory.html', 'dispensaries.html', 'events.html', 'rules.html'] + [f'{p}.html' for p in PAGES])
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
    print(f'Mirrored {len(PAGES)} Ohio pages into {args.out}')


if __name__ == '__main__':
    main()
