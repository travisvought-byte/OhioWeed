# OhioWeed.org — The Ohio cannabis guide

A source-linked, Ohio-first guide to cannabis organizations, state location records, public events and official rules. Built as a fast static site for GitHub Pages.

## Pages

- index.html — guide homepage
- directory.html — searchable Ohio cannabis organization directory
- dispensaries.html — location snapshot with city and text search
- events.html — upcoming Ohio events
- rules.html — plain-language summaries linked to official sources

## The family of free guides

Owner direction, November 28, 2026: the guides link to each other by how visitors identify. `scripts/reefer_family.py` keeps the list (`GUIDES`, `MADE_FOR_YOU`) and, on every refresh, puts the "More free guides" line in every page's footer (all eight guides; a line that comes with a mirrored page is replaced) and fills the "More help made for you" cards on `index.html` and `find.html` between their `<!--made-for-you-->` markers. `resources.html` gets its own "More help made for you" list from the directory build. Inline links: `medical.html` (Mobility Talk), `veteran-grow.html` (Veteran Resource Guide and Mobility Talk), and the mirrored `expungement.html` (Abuse of Office rights in Ohio, Veteran Resource Guide justice page).

## Data and reuse

See [SITE_DATA.md](SITE_DATA.md) for source attribution, snapshot dates and limits. Directory data is adapted from the Ohio Cannabis Ecosystem Directory under CC BY 4.0 with the required credit. Data is intentionally editorial and unranked. This site does not sell cannabis or publish paid placements in this version.

## GitHub Pages and custom domain

The repository includes the CNAME file for ohioweed.org. In GitHub, enable Pages for the main branch root (or use the included Pages workflow). At the domain registrar, point the root domain to GitHub Pages using GitHub's current custom-domain DNS instructions, then verify the domain in repository Pages settings and enable HTTPS. Do not remove existing DNS records until you know which services use them.

## Deployment

The included workflow deploys the repository root to GitHub Pages when a change reaches main. Review and merge changes before deployment.
