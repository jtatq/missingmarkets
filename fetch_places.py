#!/usr/bin/env python3
"""Build the market universe from the Census, independent of any CRM.

This is the whole point of the project. Every market list we have is
downstream of CommandCenter, so asking our own data what it is missing can
only ever return what it already knows. The Census publishes every populated
place in the country whether we have ever heard of it or not, which makes it
the only source that can answer the question.

Two files, joined on GEOID (state FIPS + place FIPS):

  ACS 5-year B01003_001E   population for every place, nationwide
  2024 Gazetteer           the place's internal point (lat/lng) and land area

Why ACS 5-year and not the annual population estimates: PEP does not publish
below the county/metro level for every place, and the 5-year table covers all
32,000-odd places including the small ones, which is exactly where the
uncovered markets turn out to live.

Gotchas worth keeping:
  - The API 302-redirects, so requests must follow redirects.
  - NAME arrives as "Acton CDP, California" -- the legal/statistical area
    description is part of the string and has to come off to get a city name
    that will join to a CRM row. It is kept as its own column because a CDP
    is not a municipality: no city hall, often no chamber, and that changes
    whether a market is sellable.
  - Nine places carry a consolidated or alternate Census name that no CRM
    row will ever match: "Louisville/Jefferson County", "Augusta-Richmond
    County", "Urban Honolulu", "Butte-Silver Bow (balance)". These are
    Louisville, Augusta, Honolulu and Butte. Left alone they are reported as
    major markets missing from CommandCenter, which is simply false, so each
    place carries an `aliases` list of the other names it answers to.
  - Puerto Rico and the island areas come back in the same call. They are
    out of selling scope and are dropped here rather than filtered later.
  - 8 of 32,325 places have ACS population but no Gazetteer row under the
    GEOID the ACS reports. Four are Massachusetts "<Name> Town city" rows,
    which the Gazetteer files under a different place code as "<Name> city"
    -- Methuen (53,043), Watertown (35,270), Amesbury, Easthampton. Those are
    real markets, so a name+state fallback recovers them. Whatever is still
    unresolved after that is NAMED in the output, never silently dropped;
    right now that is Golden Glades CDP, Florida (35,042), which the 2024
    Gazetteer does not carry at all.

CENSUS_KEY comes from the environment and is never written to this repo.
Get one free at https://api.census.gov/data/key_signup.html

Usage:
  CENSUS_KEY=... python3 fetch_places.py [out.json]
"""
import csv
import io
import json
import os
import re
import sys
import urllib.request
import zipfile

ACS_YEAR = 2023
GAZ_YEAR = 2024
ACS_URL = (f'https://api.census.gov/data/{ACS_YEAR}/acs/acs5'
           '?get=NAME,B01003_001E&for=place:*')
GAZ_URL = (f'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/'
           f'{GAZ_YEAR}_Gazetteer/{GAZ_YEAR}_Gaz_place_national.zip')

# Dropped from NAME to recover the city. Longest first so "city and borough"
# wins over "city", and ONE phrase only -- see split_name for why that matters.
# These are the Census LSAD vocabulary, not a guess.
# Case matters. The Census writes these suffixes in lowercase ("Oklahoma City
# city"), so matching case-insensitively strips the capitalized word out of a
# name that genuinely ends in it: "Carson City, Nevada" carries no suffix at
# all and would come back as "Carson". CDP is the one uppercase form.
LSAD = [
    'consolidated government', 'metropolitan government', 'metro government',
    'unified government', 'city and borough', 'town and borough',
    'charter township', 'urban county', 'zona urbana', 'municipality',
    'comunidad', 'corporation', 'plantation', 'township', 'village',
    'borough', 'district', 'city', 'town', 'gore', 'CDP',
]
# One phrase, optionally followed by "(balance)" -- which is how
# "Athens-Clarke County unified government (balance)" comes apart in a single
# pass while leaving "County" (part of the real name) alone.
LSAD_RE = re.compile(r'\s+(' + '|'.join(re.escape(x) for x in LSAD)
                     + r')(\s+\(balance\))?$')

# Island areas: out of selling scope.
OUT_OF_SCOPE = {'PR', 'VI', 'GU', 'MP', 'AS'}

# Only needed for the name fallback below, where the ACS row's state has to be
# turned into the abbreviation the Gazetteer uses.
STATE_ABBR = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'District of Columbia': 'DC', 'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI',
    'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
    'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
    'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
    'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
    'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
    'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
    'Wisconsin': 'WI', 'Wyoming': 'WY',
}


def split_name(name):
    """'Acton CDP, California' -> ('Acton', 'CDP'). Returns ('', '') on junk.

    Exactly ONE suffix comes off. Stripping repeatedly looks tidier and is
    catastrophic: "Oklahoma City city" becomes "Oklahoma City" and then
    "Oklahoma", and the same goes for Salt Lake City, Jersey City, Kansas
    City, Sioux City, Johnson City -- 82 markets, which then fail to match
    their CRM row and get reported as missing from CommandCenter. The city's
    own name is allowed to end in a word that is also an LSAD.

    The one real double suffix is the Massachusetts "<Name> Town city" form
    (Methuen, Watertown, Amesbury, Easthampton), where the Gazetteer files
    the same place as "<Name> city". That is handled explicitly, and only for
    that exact ending, so "Georgetown town" -> "Georgetown" still holds.
    """
    head = name.split(',')[0].strip()
    m = LSAD_RE.search(head)
    kind = m.group(1) if m else 'place'
    if m:
        head = head[:m.start()].strip()
    if head.endswith(' Town'):
        head = head[:-5].strip()
    return head, kind


def aliases_for(city):
    """Other names a place answers to, for the CRM join.

    The city/county consolidations are the whole reason this exists: the
    Census calls it Louisville/Jefferson County and Augusta-Richmond County,
    the CRM (and everyone else) calls it Louisville and Augusta. "Urban
    Honolulu" is the Census's CDP name for Honolulu proper. Without these the
    audit claims we have never heard of Louisville.
    """
    out = []
    if city.startswith('Urban '):
        out.append(city[6:])
    base = city.split(' (balance)')[0].strip()
    if base != city:
        out.append(base)
    if '/' in base:
        out.append(base.split('/')[0].strip())
    if '-' in base:
        head, tail = base.rsplit('-', 1)
        # Only when the tail looks like the county half of a consolidation --
        # never for ordinary hyphenated names like Winston-Salem.
        if tail.endswith('County') or tail in ('Silver Bow', 'Deer Lodge'):
            out.append(head.strip())
    return [a for a in dict.fromkeys(out) if a and a != city]


def fetch(url, timeout=120):
    req = urllib.request.Request(url, headers={'User-Agent': 'missingmarkets/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def load_gazetteer():
    """(GEOID -> row, (normalized name, state) -> row), both to the same tuple
    (usps, lat, lng, land_sqmi). The second is the fallback for the handful of
    places whose ACS place code does not match the Gazetteer's."""
    raw = fetch(GAZ_URL)
    z = zipfile.ZipFile(io.BytesIO(raw))
    text = z.read(z.namelist()[0]).decode('latin-1')
    by_geoid, by_name = {}, {}
    for row in csv.DictReader(text.splitlines(), delimiter='\t'):
        row = {(k or '').strip(): (v.strip() if isinstance(v, str) else v)
               for k, v in row.items()}
        try:
            rec = (row['USPS'], float(row['INTPTLAT']),
                   float(row['INTPTLONG']), float(row['ALAND_SQMI']))
        except (KeyError, TypeError, ValueError):
            continue
        by_geoid[row['GEOID']] = rec
        city, _ = split_name(row['NAME'] + ', x')
        if city:
            by_name.setdefault((city.lower(), row['USPS']), rec)
    return by_geoid, by_name


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else 'data/places.json'
    ck = os.environ.get('CENSUS_KEY', '').strip()
    if not ck:
        sys.exit('CENSUS_KEY is not set. See the header of this file.')

    print('fetching the Gazetteer...', flush=True)
    gaz, gaz_by_name = load_gazetteer()
    print(f'  {len(gaz):,} places with coordinates', flush=True)

    print(f'fetching ACS {ACS_YEAR} population for every place...', flush=True)
    rows = json.loads(fetch(ACS_URL + '&key=' + ck))[1:]
    print(f'  {len(rows):,} places with population', flush=True)

    places, no_coords, recovered, no_pop, dropped = [], [], [], 0, 0
    for name, pop, st_fips, pl_fips in rows:
        geoid = st_fips + pl_fips
        try:
            pop = int(pop)
        except (TypeError, ValueError):
            no_pop += 1
            continue
        if pop <= 0:
            no_pop += 1
            continue
        city, kind = split_name(name)
        if not city:
            continue
        g = gaz.get(geoid)
        if not g:
            # ACS place code does not match the Gazetteer's: fall back to the
            # name. Only the state abbreviation is trusted from the ACS row,
            # and it is the second element of the comma-split NAME.
            st_name = name.split(',')[-1].strip()
            st_abbr = STATE_ABBR.get(st_name, '')
            g = gaz_by_name.get((city.lower(), st_abbr)) if st_abbr else None
            if not g:
                no_coords.append(f'{name} ({pop:,})')
                continue
            recovered.append(name)
        usps, lat, lng, land = g
        if usps in OUT_OF_SCOPE:
            dropped += 1
            continue
        rec = {
            'geoid': geoid, 'city': city, 'state': usps, 'place_type': kind,
            'population': pop, 'lat': round(lat, 5), 'lng': round(lng, 5),
            'land_sqmi': land,
        }
        alias = aliases_for(city)
        if alias:
            rec['aliases'] = alias
        places.append(rec)

    places.sort(key=lambda p: -p['population'])
    json.dump({
        'generated': __import__('datetime').date.today().isoformat(),
        'acs_year': ACS_YEAR, 'gazetteer_year': GAZ_YEAR,
        'source': 'US Census Bureau ACS 5-year B01003 + TIGER Gazetteer',
        'count': len(places), 'places': places,
    }, open(out_path, 'w'), indent=0)

    print(f'\nwrote {out_path}: {len(places):,} in-scope places')
    print(f'  no population published: {no_pop:,}')
    print(f'  recovered by name after a GEOID miss: {len(recovered)}'
          + (f' ({", ".join(recovered)})' if recovered else ''))
    print(f'  STILL no coordinates, dropped: {len(no_coords)}'
          + (f' ({"; ".join(no_coords)})' if no_coords else ''))
    print(f'  out of selling scope (PR/VI/GU/MP/AS): {dropped:,}')
    with_alias = [p for p in places if p.get('aliases')]
    print(f'  carrying an alias for the CRM join: {len(with_alias)}'
          + (f' (e.g. {with_alias[0]["city"]} -> {with_alias[0]["aliases"][0]})'
             if with_alias else ''))
    for floor in (1000, 5000, 10000, 20000, 50000):
        print(f'  pop >= {floor:>6,}: {sum(1 for p in places if p["population"] >= floor):>6,}')


if __name__ == '__main__':
    main()
