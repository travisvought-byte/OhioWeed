#!/usr/bin/env python3
"""Accessibility finishing for every OhioWeed page. Idempotent; safe to rerun.

Owner direction, November 24, 2026: every site meets WCAG 2.1 AA as far as it can. Each page gets:

- a "Skip to main content" link as the very first thing in <body>, ahead of the OhioWeed header,
  so a keyboard user can jump past the menu (WCAG 2.4.1). It lands on the page title where the title
  sits in a hero above <main> (the mirrored pages), otherwise on <main>. A skip link that came with a
  mirrored page from the directory is replaced, because the OhioWeed header now sits in front of it;
- the styles for that link (hidden until it has keyboard focus), and less motion for visitors whose
  device asks for it.

Usage: python3 scripts/a11y.py [site-folder]
"""
import re
import sys
from pathlib import Path

MARK = '/* a11y-base */'
CSS = (MARK +
       '.a11y-skip{position:absolute;left:8px;top:-200px;z-index:10000;background:#fff;color:#173e34;'
       'padding:10px 14px;border:2px solid #173e34;border-radius:6px;font:700 17px/1.3 system-ui,sans-serif;'
       'text-decoration:underline}.a11y-skip:focus{top:8px;outline:3px solid #a07014;outline-offset:2px}'
       '@media print{.a11y-skip{display:none!important}}'
       '@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto!important}'
       '*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;'
       'transition-duration:.01ms!important;scroll-behavior:auto!important}}')
SKIP = re.compile(r'<a class="a11y-skip" href="#[^"]*">[^<]*</a>')


def _with_id(page, tag, fallback):
    """The element's id, adding `fallback` when it has none."""
    found = re.search(r'\bid="([^"]+)"', tag.group(1))
    if found:
        return page, found.group(1)
    start = tag.start() + len(tag.group(0).split()[0].rstrip('>'))
    return page[:start] + f' id="{fallback}"' + page[start:], fallback


def finish(page):
    if '</head>' not in page or not re.search(r'<body\b', page):
        return page
    page = SKIP.sub('', page)
    body = re.search(r'<body\b[^>]*>', page)
    main = re.compile(r'<main\b([^>]*)>').search(page, body.end())
    if main is None:
        return page  # forwarding and verification pages have nothing to skip to
    if MARK not in page:
        head_end = page.index('</head>')
        last = page.rfind('</style>', 0, head_end)
        page = (page[:last] + CSS + page[last:]) if last >= 0 else page.replace('</head>', '<style>' + CSS + '</style></head>', 1)
    body = re.search(r'<body\b[^>]*>', page)
    main = re.compile(r'<main\b([^>]*)>').search(page, body.end())
    title = re.compile(r'<h1\b([^>]*)>').search(page, body.end())
    if title and title.start() < main.start():
        page, target = _with_id(page, title, 'page-title')
    else:
        page, target = _with_id(page, main, 'main-content')
    body = re.search(r'<body\b[^>]*>', page)
    return page[:body.end()] + f'<a class="a11y-skip" href="#{target}">Skip to main content</a>' + page[body.end():]


def finish_site(out: Path) -> int:
    changed = 0
    for page in sorted(out.glob('*.html')):
        text = page.read_text(encoding='utf-8')
        done = finish(text)
        if done != text:
            page.write_text(done, encoding='utf-8')
            changed += 1
    return changed


if __name__ == '__main__':
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    print(f'Accessibility finishing changed {finish_site(root)} pages')
