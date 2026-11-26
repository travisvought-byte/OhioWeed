#!/usr/bin/env python3
"""Show every OhioWeed page as part of The Reefer, and load the easy-reading styles. Idempotent; safe to rerun.

Owner direction, November 26, 2026: OhioWeed should plainly show that it is The Reefer's Ohio guide,
with a link to the-reefer.com in the header and the footer, and read well for older visitors.
Each page gets:
- assets/easy-read.css, linked as the last thing in <head> so it wins over the page's own styles;
- a slim bar at the very top (after the skip link): "OhioWeed is The Reefer's Ohio guide";
- a footer note naming The Reefer and saying the site is free and open source, with an offer to help.

Runs after scripts/a11y.py in the mirror and again at the end of the refresh workflow.
Usage: python3 scripts/reefer_family.py [site-folder]
"""
import re
import sys
from pathlib import Path

CSS_LINK = '<link rel="stylesheet" href="assets/easy-read.css">'
BAR = ('<div class="reefer-bar" role="region" aria-label="About this site"><div class="rb-in">'
       '<img src="assets/the-reefer/mark-96.png" alt="" width="32" height="32">'
       '<span>OhioWeed is <strong>The Reefer’s Ohio guide</strong>. The Reefer covers every state.</span>'
       '<a href="https://the-reefer.com/">Go to The Reefer</a></div></div>')
FOOT = ('<div class="reefer-foot">'
        '<p><strong>Part of The Reefer.</strong> OhioWeed is The Reefer’s Ohio guide. '
        'For every other state, go to <a href="https://the-reefer.com/">the-reefer.com</a>.</p>'
        '<p><strong>Free and open source.</strong> You are welcome to copy anything on this site for your own '
        'site or group. Travis will help you set it up for free: '
        '<a href="mailto:VeteranHomeGuardians@gmail.com">email VeteranHomeGuardians@gmail.com</a> or '
        '<a href="https://github.com/travisvought-byte/ohioweed">get the code on GitHub</a>.</p></div>')
OLD = re.compile(r'<link rel="stylesheet" href="assets/easy-read\.css">|<div class="reefer-bar"[^>]*>.*?</div></div>'
                 r'|<div class="reefer-foot">.*?</p></div>', re.S)


def finish(page):
    if '</head>' not in page or '<body' not in page:
        return page
    page = OLD.sub('', page)
    if '<meta http-equiv="refresh"' in page:
        return page
    page = page.replace('</head>', CSS_LINK + '</head>', 1)
    skip = re.search(r'<a class="a11y-skip"[^>]*>[^<]*</a>', page)
    at = skip.end() if skip else re.search(r'<body\b[^>]*>', page).end()
    page = page[:at] + BAR + page[at:]
    end = page.rfind('</footer>')
    if end >= 0:
        # inside the footer's outer wrapper, after its last block
        inner = page.rfind('</div>', 0, end)
        page = page[:inner] + FOOT + page[inner:] if inner > page.rfind('<footer', 0, end) else page[:end] + FOOT + page[end:]
    return page


def finish_site(out: Path) -> int:
    changed = 0
    for path in sorted(out.glob('*.html')):
        text = path.read_text(encoding='utf-8')
        done = finish(text)
        if done != text:
            path.write_text(done, encoding='utf-8')
            changed += 1
    return changed


if __name__ == '__main__':
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    print(f'The Reefer link and easy reading changed {finish_site(root)} pages')
