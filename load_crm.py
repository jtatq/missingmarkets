#!/usr/bin/env python3
"""Read a CommandCenter territory export into normalized rows.

What this export is, and is not: it is the list of territories the CRM holds,
and in practice that is the list of what is TAKEN. In the 2026-11-05 file,
2,884 of 2,916 rows are Assigned / Active / Holding and only 32 are Available.
So "absent from this file" means "no rep holds it", which is not the same as
"nobody can sell there" -- the market next door to a rep's city is absent too.
build_coverage.py is what separates those; this file only reads.

Three repairs, each for a real defect in the feed:

  - Double-encoded UTF-8. "La CaÃ±ada Flintridge" is in the live data. Latin-1
    is the exact inverse of the extra encoding pass, so round-tripping
    restores it. Attempted only on strings carrying the Ã/Â markers and kept
    only when the round-trip succeeds.
  - Status casing. The 8/31/2026 export switched to ACTIVE/ASSIGNED; this one
    carries both cases in the same file (335 ACTIVE and 240 Active). They are
    one status and are canonicalized to title case. An unrecognized status
    passes through untouched and still counts as taken.
  - Canadian rows. 12 of them, and they are served by a separate instance with
    its own prospect universe. Dropped, with a count.

Zero coordinates are not a location. The export sends 0,0 for unknown, and a
market at 0,0 would land in the Gulf of Guinea and read as 4,000 miles from
everything -- which would make it look like virgin territory. Those rows are
kept for the name match and excluded from the distance index.
"""
import csv
import os
import sys

# Run with -I (isolated) so nothing is imported from PYTHONPATH or the user
# site -- the CRM export is untrusted input. -I also drops this script's own
# directory, so the sibling helper module is put back explicitly.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mc_util import key

CANADA = {'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT'}
KNOWN_STATUS = ('available', 'assigned', 'active', 'holding')


def demojibake(s):
    for _ in range(3):
        if not s or ('Ã' not in s and 'Â' not in s):
            break
        try:
            fixed = s.encode('latin-1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if fixed == s:
            break
        s = fixed
    return s


def load(path):
    """Returns (rows, stats). Each row: city, state, status, rep, lat, lng, mkey."""
    rows, stats = [], {'read': 0, 'canada': 0, 'no_coords': 0, 'duplicate_key': 0}
    seen = {}
    for r in csv.DictReader(open(path, encoding='utf-8-sig')):
        stats['read'] += 1
        state = (r.get('state') or '').strip().upper()
        if state in CANADA:
            stats['canada'] += 1
            continue
        city = demojibake((r.get('city') or '').strip())
        if not city or not state:
            continue
        status = (r.get('status') or '').strip()
        if status.lower() in KNOWN_STATUS:
            status = status.title()
        try:
            lat, lng = float(r.get('lat') or 0), float(r.get('lng') or 0)
        except ValueError:
            lat = lng = 0.0
        if not lat or not lng:
            stats['no_coords'] += 1
            lat = lng = None
        k = key(city, state)
        row = {
            'city': city, 'state': state, 'status': status, 'mkey': k,
            'rep': (demojibake((r.get('assignedRepName') or '').strip())
                    or demojibake((r.get('holdingRepName') or '').strip())),
            'lat': lat, 'lng': lng,
            'population_crm': int(r['population']) if (r.get('population') or '').isdigit() else 0,
            'last_worked': (r.get('lastWorkedDate') or '').strip(),
        }
        if k in seen:
            stats['duplicate_key'] += 1
            # Prefer the row that actually has coordinates.
            if seen[k]['lat'] is None and lat:
                seen[k].update(row)
            continue
        seen[k] = row
        rows.append(row)
    stats['kept'] = len(rows)
    return rows, stats


if __name__ == '__main__':
    rows, stats = load(sys.argv[1])
    import collections
    print(stats)
    print('statuses:', dict(collections.Counter(r['status'] for r in rows)))
    print('states:', len(set(r['state'] for r in rows)))
    print('reps:', len(set(r['rep'] for r in rows if r['rep'])))
    bad = [r for r in rows if 'Ã' in r['city'] or 'Â' in r['city']]
    print('still mojibaked:', len(bad))
