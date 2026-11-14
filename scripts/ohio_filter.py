"""Reduce data/directory.json to the Ohio records OhioWeed already publishes.

Keeps exactly the organizations passed in as Ohio ids (see mirror_directory.ohio_org_ids),
their Ohio locations and services, relationships between them, Ohio events and
rules, and the evidence those records cite. Other states are removed from the copy only.
"""
import json, sys
from pathlib import Path

def filter_directory(root, ohio_ids_file):
    root = Path(root)
    d = json.loads((root / 'data/directory.json').read_text(encoding='utf-8'))
    ohio = json.loads(Path(ohio_ids_file).read_text(encoding='utf-8'))
    keep_orgs = {r['id'] for r in ohio}
    legacy = {}
    for o in d['organizations']:
        for lid in o.get('legacy_ids', []):
            legacy[lid] = o['id']
    keep_orgs = {legacy.get(i, i) for i in keep_orgs}
    keep_orgs &= {o['id'] for o in d['organizations']}
    assert 516 <= len(keep_orgs), len(keep_orgs)
    # Ohio dispensary locations belong to operators that are not in the 516 list; keep their owners too.
    oh_locs_all = [l for l in d['locations'] if l.get('state') == 'OH']
    keep_orgs |= {l['organization_id'] for l in oh_locs_all}

    orgs = [o for o in d['organizations'] if o['id'] in keep_orgs]
    locs = oh_locs_all
    svcs = [s for s in d['services'] if s.get('organization_id') in keep_orgs
            and (not s.get('listed_in') or 'OH' in s['listed_in'])]
    kept_locs = {l['id'] for l in locs}
    kept_svcs = {s['id'] for s in svcs}
    rels = [r for r in d['relationships'] if r['organization_a_id'] in keep_orgs and r['organization_b_id'] in keep_orgs]
    events = [e for e in d['events'] if e.get('state') == 'OH']
    rules = [r for r in d['rules'] if r.get('state') == 'OH']
    states = [s for s in d['states'] if s['code'] == 'OH']
    aliases = [a for a in d['aliases'] if a.get('new_id') in keep_orgs or a.get('old_id') in keep_orgs]

    subjects = keep_orgs | kept_locs | kept_svcs | {r['id'] for r in rels} | {e['id'] for e in events} | {r['id'] for r in rules}
    cited = set()
    for coll in (orgs, locs, svcs, rels, events, rules):
        for item in coll:
            cited.update(item.get('evidence_ids', []) or [])
    evidence = [e for e in d['evidence'] if e['id'] in cited or e.get('subject_id') in subjects]

    out = dict(d)
    out.update(organizations=orgs, locations=locs, services=svcs, relationships=rels,
               events=events, rules=rules, states=states, aliases=aliases, evidence=evidence)
    (root / 'data/directory.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"orgs {len(orgs)}, locations {len(locs)}, services {len(svcs)}, relationships {len(rels)}, "
          f"events {len(events)}, rules {len(rules)}, evidence {len(evidence)}/{len(d['evidence'])}")
    for k in ['resource_routes', 'event_routes', 'event_spotlights', 'pathways']:
        print(k, json.dumps(d[k], ensure_ascii=False)[:300])


if __name__ == '__main__':
    filter_directory(sys.argv[1], sys.argv[2])
