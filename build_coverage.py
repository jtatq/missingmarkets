#!/usr/bin/env python3
"""The audit: which real markets does CommandCenter have no row for?

Four inputs, joined on the normalized market key:

  data/places.json                        the Census universe (31,552 places)
  data/commandcenter-*.csv                what the CRM holds today
  data/vendor/stores.json                 the anchor-store join, 7 miles
  data/vendor/territories-available.json  ONLY to classify, never to build

That third line matters. A market absent from the CRM is not automatically an
opportunity: 2,486 of them sit inside a listed market's 7-mile trade area --
the same geofence the store join, the basin collision test and /gaps all use.
Those are infill in a rep's existing territory, not new ground. The audit is
the subset that is BOTH absent from the CRM and far enough from everything in
it to stand on its own.

The fourth line is what keeps the output honest. Sorted by population, the
absent list opens with San Jose, Salinas, Peoria AZ and Goodyear AZ -- markets
CommandCenter DROPPED between the 10/04 and 11/05 exports, not markets it
never had. Reporting those as untapped opportunity would be wrong, so every
row is classed:

  A never-listed      absent from the CRM and from Market Finder. Unexplored.
  B unlisted-prospect absent from the CRM, Market Finder has it as Available.
  C dropped           absent from this export, but Market Finder marks it
                      Assigned/Active/Holding -- the CRM listed it before.
                      Needs reconciliation, not prospecting.

Usage:
  python3 -I build_coverage.py data/commandcenter-territories-2026-11-05.csv
"""
import collections
import csv
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import load_crm
from mc_util import GridIndex, key, tz_for

HERE = os.path.dirname(os.path.abspath(__file__))
POP_FLOOR = 5000          # JT's call: below this is not a sellable market
TRADE_AREA_MI = 7.0       # the geofence everything else in the product uses
ANCHOR_MI = 7.0

# Best anchor when several are in range. Warehouse club first: a Costco trade
# area is the strongest signal we have, a Walmart the weakest of the five.
TIER_RANK = ['club', 'national-upscale', 'regional-upscale',
             'dominant-anchor', 'mainstream-anchor']


def load_json(*parts):
    return json.load(open(os.path.join(HERE, *parts)))


def main():
    crm_path = sys.argv[1] if len(sys.argv) > 1 else \
        'data/commandcenter-territories-2026-11-05.csv'

    places = load_json('data', 'places.json')
    crm_rows, crm_stats = load_crm.load(crm_path)
    stores = load_json('data', 'vendor', 'stores.json')
    snapshot = load_json('data', 'vendor', 'territories-available.json')

    crm_keys = {r['mkey'] for r in crm_rows}
    crm_index = GridIndex((r['lat'], r['lng'], r) for r in crm_rows
                          if r['lat'] and r['lng'])
    store_index = GridIndex((s['lat'], s['lng'], s) for s in stores['stores']
                            if s.get('lat') and s.get('lng'))
    mf_status = {key(t['city'], t['state']): t.get('status', '')
                 for t in snapshot['territories']}

    universe = [p for p in places['places'] if p['population'] >= POP_FLOOR]
    out, listed, guards = [], 0, collections.Counter()

    for p in universe:
        k = key(p['city'], p['state'])
        # A place answers to its aliases too, or the city/county consolidations
        # read as missing: the Census says Louisville/Jefferson County and
        # Augusta-Richmond County where the CRM says Louisville and Augusta.
        all_keys = [k] + [key(a, p['state']) for a in p.get('aliases', ())]
        if any(x in crm_keys for x in all_keys):
            listed += 1
            continue

        # Nearest market the CRM does hold. Widen the ring until something is
        # found: a bounded index returns nothing for a genuinely remote town,
        # and "nothing within 100 miles" is a finding, not a failure.
        d = rec = None
        for span in (3, 6, 12):
            d, rec = crm_index.nearest(p['lat'], p['lng'], span=span)
            if d is not None:
                break

        anchors = store_index.within(p['lat'], p['lng'], ANCHOR_MI)
        top = min(anchors, key=lambda a: (TIER_RANK.index(a[1]['tier'])
                                          if a[1]['tier'] in TIER_RANK else 9,
                                          a[0])) if anchors else None

        mf = next((mf_status[x] for x in all_keys if x in mf_status), '')
        if not mf:
            cls = 'A never-listed'
        elif mf == 'Available':
            cls = 'B unlisted-prospect'
        else:
            cls = f'C dropped ({mf} in Market Finder)'

        notes = []
        if not anchors:
            notes.append('no_anchor')
        if p['place_type'].upper() == 'CDP':
            notes.append('cdp_not_a_municipality')
        if p['state'] in ('AK', 'HI'):
            notes.append('outside_lower_48')
        standalone = d is None or d >= TRADE_AREA_MI
        if not standalone:
            notes.append('infill_inside_existing_trade_area')
        if d is None:
            # Nothing within the widest ring searched (~400 miles). Hawaii has
            # no CRM row at all; so do stretches of Alaska and west Texas.
            notes.append('no_listed_market_within_400mi')
        if p.get('aliases'):
            notes.append('census_name_alias=' + '|'.join(p['aliases']))

        if p['population'] <= 0:
            guards['population missing'] += 1
        if not p['lat'] or not p['lng']:
            guards['coordinates missing'] += 1

        out.append({
            'city': p['city'], 'state': p['state'], 'place_type': p['place_type'],
            'population': p['population'],
            'zone': tz_for(p['state'], p['lat'], p['lng']),
            'lat': p['lat'], 'lng': p['lng'], 'class': cls,
            'standalone': standalone,
            'anchor_brand': top[1]['brand'] if top else '',
            'anchor_tier': stores['tiers'].get(top[1]['tier'], '') if top else '',
            'anchor_miles': round(top[0], 1) if top else '',
            'anchor_count': len(anchors),
            'nearest_listed_city': rec['city'] if rec else '',
            'nearest_listed_state': rec['state'] if rec else '',
            'nearest_listed_miles': round(d, 1) if d is not None else '',
            'nearest_listed_rep': rec['rep'] if rec else '',
            'nearest_listed_status': rec['status'] if rec else '',
            'notes': ' '.join(notes),
        })

    out.sort(key=lambda r: -r['population'])
    cols = ['city', 'state', 'place_type', 'population', 'zone', 'lat', 'lng',
            'class', 'standalone', 'anchor_brand', 'anchor_tier', 'anchor_miles',
            'anchor_count', 'nearest_listed_city', 'nearest_listed_state',
            'nearest_listed_miles', 'nearest_listed_rep', 'nearest_listed_status',
            'notes']

    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    # The BOM is not decoration: without it Excel reads the file as cp1252 and
    # Española and Cañon City arrive mangled.
    with open(os.path.join(HERE, 'out', 'coverage.csv'), 'w', newline='',
              encoding='utf-8') as fh:
        fh.write('﻿')
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)

    standalone = [r for r in out if r['standalone']]
    anchored = [r for r in standalone if r['anchor_count']]
    summary = {
        'generated': datetime.date.today().isoformat(),
        'crm_export': os.path.basename(crm_path),
        'acs_year': places['acs_year'], 'gazetteer_year': places['gazetteer_year'],
        'pop_floor': POP_FLOOR, 'trade_area_miles': TRADE_AREA_MI,
        'crm_rows': crm_stats,
        'universe_at_floor': len(universe),
        'listed_in_crm': listed,
        'absent_from_crm': len(out),
        'absent_but_infill': len(out) - len(standalone),
        'standalone_missing': len(standalone),
        'standalone_missing_anchored': len(anchored),
        'by_class': dict(collections.Counter(r['class'].split(' ')[0] for r in anchored)),
        'by_zone': dict(collections.Counter(r['zone'] for r in anchored)),
        'by_state': dict(collections.Counter(r['state'] for r in anchored).most_common()),
        'guards': dict(guards),
    }
    json.dump({'summary': summary, 'markets': out},
              open(os.path.join(HERE, 'out', 'coverage.json'), 'w'), indent=1)

    pct = 100.0 * listed / len(universe)
    print(f'Census universe at pop >= {POP_FLOOR:,}: {len(universe):,} places')
    print(f'  listed in CommandCenter:        {listed:,}  ({pct:.0f}%)')
    print(f'  absent from CommandCenter:      {len(out):,}')
    print(f'    inside a listed trade area:   {len(out) - len(standalone):,}  (infill, not new)')
    print(f'    STANDALONE and missing:       {len(standalone):,}')
    print(f'      with an anchor store <={ANCHOR_MI:.0f}mi: {len(anchored):,}   <- the list')
    print()
    for cls, n in sorted(collections.Counter(r['class'] for r in anchored).items()):
        print(f'   {cls:<42} {n:>5}')
    print()
    print('  anchored standalone by zone:', summary['by_zone'])
    if guards:
        print('  GUARDS TRIPPED:', dict(guards))
    else:
        print('  guards: 0 populations missing, 0 coordinates missing')
    print(f'\nwrote out/coverage.csv ({len(out):,} rows) and out/coverage.json')


if __name__ == '__main__':
    main()
