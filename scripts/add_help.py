#!/usr/bin/env python3
"""Put the suicide and homelessness help block on every OhioWeed page. Idempotent; safe to rerun.

Owner direction, November 17, 2026: every site carries help for people thinking about
suicide and people with no safe place to sleep.

Pages mirrored from ohio-cannabis-directory arrive with the block already in place (its
directory_brand.help_now()). Pages written in this repository get the same words here,
directly above the site footer. Either way, every page ends up with exactly one block;
the run stops with an error if a page would be published without one or with two.

Sources, each read on November 17, 2026:
- 988lifeline.org: call or text 988, 24 hours a day, free and confidential.
- veteranscrisisline.net: dial 988, then press 1.
- hud.gov/contactus: dial 2-1-1 and press 6 for homeless services; the Find Shelter tool.
- usa.gov/emergency-housing: National Call Center for Homeless Veterans, 1-877-424-3838,
  24 hours a day.

Usage: python3 scripts/add_help.py [site-folder]
"""
import re
import sys
from pathlib import Path

# Each link is underlined and bold so it stands out on any page's own styling; short ones never break across lines.
_WRAP = ' style="color:#0b4f6c;font-weight:600;text-decoration:underline"'
_LINK = ' style="color:#0b4f6c;font-weight:600;text-decoration:underline;white-space:nowrap"'
BLOCK = ('<aside class="help-now" aria-label="Need help now?" style="box-sizing:border-box;width:calc(100% - 32px);max-width:1120px;margin:24px auto;padding:12px 16px;'
         'border:1px solid #ccc;border-left:6px solid #7a1f1f;border-radius:6px;background:#fff;color:#1b1b1b;'
         'font-size:.95rem;line-height:1.5;text-align:left">'
         '<strong>Need help now?</strong> Thinking about suicide, or in any crisis: '
         '<a href="tel:988"' + _LINK + '>call</a> or <a href="sms:988"' + _LINK + '>text 988</a>, any time. '
         'Veterans: dial 988, then press 1. No safe place to sleep tonight: '
         '<a href="tel:211"' + _LINK + '>dial 211</a> and press 6 for homeless services, or use '
         '<a href="https://www.hud.gov/findshelter"' + _WRAP + '>HUD’s Find Shelter tool</a>. Veterans: '
         '<a href="tel:+18774243838"' + _LINK + '>1-877-424-3838</a>, 24 hours a day.</aside>')
HELP = '<!--help-->' + BLOCK + '<!--/help-->'
FOOTER = '<footer class="site-footer"'


def add_help(out: Path) -> int:
    count = 0
    for page in sorted(out.glob('*.html')):
        text = re.sub(r'<!--help-->.*?<!--/help-->', '', page.read_text(encoding='utf-8'), flags=re.S)
        if 'class="help-now"' not in text:
            at = text.rfind(FOOTER)
            if at < 0:
                raise SystemExit(f'{page.name}: no site footer to put the help block above')
            text = text[:at] + HELP + text[at:]
        found = text.count('class="help-now"')
        if found != 1:
            raise SystemExit(f'{page.name}: expected one help block, found {found}')
        for link in ('href="tel:988"', 'href="sms:988"', 'href="tel:211"', 'href="tel:+18774243838"'):
            if link not in text:
                raise SystemExit(f'{page.name}: the help block is missing {link}')
        page.write_text(text, encoding='utf-8')
        count += 1
    return count


if __name__ == '__main__':
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent)
    print(f'Help block on {add_help(root)} pages')
