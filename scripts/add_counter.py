#!/usr/bin/env python3
"""Add the visit counter to every OhioWeed page. Idempotent; safe to rerun.

Owner direction, November 16, 2026: every site reports page visits to the shared
GoatCounter dashboard (vhg-guide.goatcounter.com). OhioWeed's paths start
/ohioweed.org/ so they never mix with the other sites there. Page visits only:
no cookies, no storage, no click or form data, and query strings are dropped from
paths and referrers. The directory's own click-tracking script stays removed
(see mirror_directory.py), so nothing is counted twice.

Usage: python3 scripts/add_counter.py [site-folder]
"""
import re
import sys
from pathlib import Path

COUNTER = ('<!--gc--><script>window.goatcounter={path:function(){return "/ohioweed.org"+location.pathname},'
           'referrer:function(){try{var u=new URL(document.referrer);return u.origin+u.pathname}catch(e){return ""}}};</script>'
           '<script data-goatcounter="https://vhg-guide.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script><!--/gc-->')


def add_counter(out: Path) -> int:
    count = 0
    for page in sorted(out.glob('*.html')):
        text = re.sub(r'<!--gc-->.*?<!--/gc-->', '', page.read_text(encoding='utf-8'), flags=re.S)
        if text.count('</head>') != 1:
            raise SystemExit(f'{page.name}: expected one </head>')
        page.write_text(text.replace('</head>', COUNTER + '</head>', 1), encoding='utf-8')
        count += 1
    return count


if __name__ == '__main__':
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    print(f'Counter on {add_counter(root)} pages')
