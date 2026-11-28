#!/usr/bin/env python3
"""Show every OhioWeed page as part of The Reefer, and load the easy-reading styles. Idempotent; safe to rerun.

Owner direction, November 26, 2026: OhioWeed should plainly show that it is The Reefer's Ohio guide,
with a link to the-reefer.com in the header and the footer, and read well for older visitors.
Each page gets:
- assets/easy-read.css, linked as the last thing in <head> so it wins over the page's own styles;
- a slim bar at the very top (after the skip link): "OhioWeed is The Reefer's Ohio guide";
- a footer note naming The Reefer and saying the site is free and open source, with an offer to help;
- the family's footer line, "More free guides: ...", naming every free guide in the family (owner direction,
  November 28, 2026: guides link to each other by how visitors identify). OhioWeed is not one of the eight, so
  the line names all of them. A line that came with a mirrored page from the directory is replaced, so each
  page carries one;
- on pages that hold the <!--made-for-you--><!--/made-for-you--> markers (index.html and find.html), the
  "More help made for you" cards: how a visitor may describe themselves, and the guide made for them.

Runs after scripts/a11y.py in the mirror and again at the end of the refresh workflow.
404.html is served at whatever address was mistyped, at any depth, so its stylesheet and image
links start at the site root (/assets/...) instead of beside the page.
Usage: python3 scripts/reefer_family.py [site-folder]
"""
import re
import sys
from pathlib import Path

CSS_LINK = '<link rel="stylesheet" href="assets/easy-read.css">'
ROOTED = {'404.html'}  # served at any depth, so its links start at the site root
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
# The family of free guides, in the family's shared order: (key, name, address, who it is for).
# Abuse of Office covers Ohio, the state this guide serves.
GUIDES = [
    ('vets', 'Veteran Resource Guide', 'https://guide.vethomeguard.org/', 'veterans and their families'),
    ('mob', 'Mobility Talk', 'https://mobilitytalk.org/', 'disability and mobility help'),
    ('ymt', 'Yoga Mom Talk', 'https://www.yogamomtalk.com/', 'moms, parents and families'),
    ('nina', "Nina's Map", 'https://ninas-map.com/', 'Native and Indigenous people'),
    ('aoo', 'Abuse of Office', 'https://abuseofoffice.org/', 'rights with police, jails and courts in Ohio'),
    ('reefer', 'The Reefer', 'https://the-reefer.com/', 'cannabis laws and help in every state'),
    ('earth', 'Earth Rules', 'https://earthrules.org/', 'everyday adult know-how'),
    ('bingo', 'Find Bingo', 'https://www.findbingo.org/', 'bingo games and senior centers near you'),
]
RELATED = ('<!--related--><p class="related">More free guides: '
           + ' · '.join(f'<a href="{url}">{name}</a> ({who})' for _, name, url, who in GUIDES) + '</p><!--/related-->')

# "More help made for you": (guide key, decorative symbol, how the visitor may describe themselves, search words,
# what the guide offers, drawn from each guide's own description). Deep pages that fit better than a guide's home
# page are in MADE_FOR_YOU_PAGES; each exists in that guide's repository.
MADE_FOR_YOU = [
    ('vets', '🎖️', 'A veteran or military family', 'veteran veterans military va benefits family service',
     'Free help for veterans and families in every state: claims, VA health care, housing and long-term care.'),
    ('mob', '♿', 'Living with a disability, or caring for someone who is', 'disability disabled wheelchair mobility caregiver ada',
     'Free disability help in every state: benefits, equipment repair, rides, in-home help and your rights.'),
    ('nina', '🗺️', 'Native American, Alaska Native or Indigenous', 'native american indigenous tribal tribe alaska native first nations',
     'A free map for First Peoples: Nations, Indian health clinics, community centers and help.'),
    ('aoo', '⚖️', 'Arrested, jailed or dealing with a court in Ohio', 'arrested arrest jail police court rights officials',
     'Your rights when arrested or jailed in Ohio, and how to hold officials to account.'),
    ('ymt', '👪', 'A mom, parent or caregiver of kids', 'mom moms mother parent parents kids children family pregnant',
     'Free help for moms and families in every state: food, rent, child care and disability help.'),
    ('reefer', '🌎', 'Outside Ohio, or traveling with cannabis', 'other states travel national every state reefer',
     'Plain cannabis answers for every state: the law, medical cards, record clearing and help.'),
    ('earth', '🧭', 'Figuring out adult life', 'adult life taxes credit moving turning 18 how to',
     'A plain guide to what everyone is expected to know: taxes, credit, moving, checkups and more.'),
    ('bingo', '🎲', 'An older adult looking for bingo or a senior center', 'bingo senior seniors center older adults games',
     'Bingo games and senior centers near you.'),
]
MADE_FOR_YOU_PAGES = {'aoo': ('https://abuseofoffice.org/rights.html', 'Abuse of Office (Ohio)'),
                      'bingo': ('https://www.findbingo.org/ohio/', 'Find Bingo (Ohio)')}
MFY = re.compile(r'<!--made-for-you-->.*?<!--/made-for-you-->', re.S)


def made_for_you():
    """The cards, in the find-card style both pages already use. The symbol is decorative; the words carry it."""
    guides = {key: (url, name) for key, name, url, _ in GUIDES}
    cards = []
    for key, symbol, who, words, what in MADE_FOR_YOU:
        url, name = MADE_FOR_YOU_PAGES.get(key, guides[key])
        cards.append(f'<a class="find-card" href="{url}" data-k="{words}"><h3><span class="find-icon" aria-hidden="true">{symbol}</span> {who}</h3>'
                     f'<p><strong>{name}.</strong> {what}</p><span class="find-go">Open {name} ↗</span></a>')
    return '<!--made-for-you-->' + ''.join(cards) + '<!--/made-for-you-->'


OLD = re.compile(r'<link rel="stylesheet" href="/?assets/easy-read\.css">|<div class="reefer-bar"[^>]*>.*?</div></div>'
                 r'|<div class="reefer-foot">.*?</p></div>|<!--related-->.*?<!--/related-->', re.S)


def finish(page, root=''):
    if '</head>' not in page or '<body' not in page:
        return page
    page = OLD.sub('', page)
    if '<meta http-equiv="refresh"' in page:
        return page
    page = MFY.sub(lambda m: made_for_you(), page)
    css_link, bar = (CSS_LINK.replace('"assets/', '"/assets/'), BAR.replace('"assets/', '"/assets/')) if root else (CSS_LINK, BAR)
    page = page.replace('</head>', css_link + '</head>', 1)
    skip = re.search(r'<a class="a11y-skip"[^>]*>[^<]*</a>', page)
    at = skip.end() if skip else re.search(r'<body\b[^>]*>', page).end()
    page = page[:at] + bar + page[at:]
    end = page.rfind('</footer>')
    if end >= 0:
        # inside the footer's outer wrapper, after its last block
        inner = page.rfind('</div>', 0, end)
        page = page[:inner] + FOOT + RELATED + page[inner:] if inner > page.rfind('<footer', 0, end) else page[:end] + FOOT + RELATED + page[end:]
    return page


def finish_site(out: Path) -> int:
    changed = 0
    for path in sorted(out.glob('*.html')):
        text = path.read_text(encoding='utf-8')
        done = finish(text, '/' if path.name in ROOTED else '')
        if done != text:
            path.write_text(done, encoding='utf-8')
            changed += 1
    return changed


if __name__ == '__main__':
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    print(f'The Reefer link and easy reading changed {finish_site(root)} pages')
