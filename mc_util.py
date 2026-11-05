"""Shared helpers for the coverage audit.

These four are deliberate COPIES of logic that already exists in the
market-finder repo rather than imports of it. This project has to be able to
answer "what is CommandCenter missing?" without market-finder in the loop, and
the two are allowed to diverge; an import would quietly couple them again.

Origins, for anyone reconciling a difference later:
  key()       deploy/build-territories-snapshot.py:66  (and mkey() in index.html)
  tz_for()    deploy/tz_util.py
  miles()     the haversine in gaps.html
  GridIndex   the half-degree grid in gaps.html's recompute()

Keep key() byte-identical to market-finder's. It is the join between this
project's Census universe and both the CRM export and market-finder's
snapshot; if the two normalizers disagree, every count in out/findings.md is
wrong in a way that looks plausible.
"""
import collections
import math
import re
import unicodedata

EARTH_MI = 3958.8

STATE_TZ = {
    'CT': 'Eastern', 'DE': 'Eastern', 'DC': 'Eastern', 'FL': 'Eastern', 'GA': 'Eastern',
    'IN': 'Eastern', 'KY': 'Eastern', 'ME': 'Eastern', 'MD': 'Eastern', 'MA': 'Eastern',
    'MI': 'Eastern', 'NH': 'Eastern', 'NJ': 'Eastern', 'NY': 'Eastern', 'NC': 'Eastern',
    'OH': 'Eastern', 'PA': 'Eastern', 'RI': 'Eastern', 'SC': 'Eastern', 'VT': 'Eastern',
    'VA': 'Eastern', 'WV': 'Eastern',
    'AL': 'Central', 'AR': 'Central', 'IL': 'Central', 'IA': 'Central', 'KS': 'Central',
    'LA': 'Central', 'MN': 'Central', 'MS': 'Central', 'MO': 'Central', 'NE': 'Central',
    'ND': 'Central', 'OK': 'Central', 'SD': 'Central', 'TN': 'Central', 'TX': 'Central',
    'WI': 'Central',
    'AZ': 'Mountain', 'CO': 'Mountain', 'ID': 'Mountain', 'MT': 'Mountain',
    'NM': 'Mountain', 'UT': 'Mountain', 'WY': 'Mountain',
    'CA': 'Pacific', 'NV': 'Pacific', 'OR': 'Pacific', 'WA': 'Pacific',
    'AK': 'Alaska', 'HI': 'Hawaii',
}


def key(city, state):
    """Normalized market key. Accents fold so Espanola and Española are one
    market, and 'saint' collapses to 'st' because the CRM spells it both ways.
    """
    c = unicodedata.normalize('NFKD', str(city))
    c = ''.join(ch for ch in c if not unicodedata.combining(ch)).lower()
    c = re.sub(r'[^a-z0-9 ]+', ' ', c)
    c = re.sub(r'\bsaint\b', 'st', c)
    c = re.sub(r'\s+', ' ', c).strip()
    return c + '|' + str(state).lower().strip()


def tz_for(state, lat=None, lng=None):
    """Time zone a rep actually dials into. Longitude refines the split states."""
    st = (state or '').upper()
    if lng:
        if st == 'FL' and lng < -85.1:
            return 'Central'
        if st == 'TN' and lng > -85.3:
            return 'Eastern'
        if st == 'KY' and lng < -86.3:
            return 'Central'
        if st == 'TX' and lng < -105:
            return 'Mountain'
        if st == 'ID' and lng < -116 and (lat or 0) > 45.5:
            return 'Pacific'
        if st == 'OR' and lng > -117.3:
            return 'Mountain'
        if st in ('NE', 'KS', 'SD', 'ND') and lng < -100.5:
            return 'Mountain'
    return STATE_TZ.get(st, '')


def miles(lat1, lng1, lat2, lng2):
    d = math.pi / 180
    h = (math.sin((lat2 - lat1) * d / 2) ** 2
         + math.cos(lat1 * d) * math.cos(lat2 * d) * math.sin((lng2 - lng1) * d / 2) ** 2)
    return EARTH_MI * 2 * math.asin(math.sqrt(max(0.0, h)))


class GridIndex:
    """Half-degree bucket index for nearest-neighbour over tens of thousands of
    points. A full cross join of 32,000 places against 2,900 CRM rows is 94
    million haversines; bucketing makes it linear and finishes in a second.

    Each bucket is ~34 miles tall, so a search ring of +/-1 bucket covers any
    radius up to ~34 miles. Callers asking for more must widen `span`, and
    nearest() returns None beyond the ring it searched -- it is a bounded
    nearest, not a global one. That is deliberate: "nothing within 100 miles"
    is the answer we want, not a 900-mile drive to the nearest market.
    """

    def __init__(self, points):
        """points: iterable of (lat, lng, payload)."""
        self.cells = collections.defaultdict(list)
        self.n = 0
        for lat, lng, payload in points:
            self.cells[(int(lat * 2), int(lng * 2))].append((lat, lng, payload))
            self.n += 1

    def nearest(self, lat, lng, span=3):
        """Closest point within `span` buckets: (miles, payload), or (None, None)."""
        bx, by = int(lat * 2), int(lng * 2)
        best_d, best_p = None, None
        for dx in range(-span, span + 1):
            for dy in range(-span, span + 1):
                for a, b, payload in self.cells.get((bx + dx, by + dy), ()):
                    d = miles(lat, lng, a, b)
                    if best_d is None or d < best_d:
                        best_d, best_p = d, payload
        return best_d, best_p

    def within(self, lat, lng, radius_mi):
        """Every point within radius_mi: list of (miles, payload), nearest first."""
        span = max(1, int(radius_mi / 34) + 1)
        bx, by = int(lat * 2), int(lng * 2)
        hits = []
        for dx in range(-span, span + 1):
            for dy in range(-span, span + 1):
                for a, b, payload in self.cells.get((bx + dx, by + dy), ()):
                    d = miles(lat, lng, a, b)
                    if d <= radius_mi:
                        hits.append((d, payload))
        hits.sort(key=lambda h: h[0])
        return hits
