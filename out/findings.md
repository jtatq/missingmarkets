# What CommandCenter is missing

Audit of the **2026-11-05** CommandCenter territory export against every
populated place the US Census publishes. Generated 2026-11-05.

---

## The headline

**CommandCenter holds a row for 2,592 of the 6,745 US places with 5,000 or
more residents — 38%.**

That number on its own invites the wrong conclusion, so here is the whole
funnel:

| | |
|---|---|
| Census places, pop 5,000+ | 6,745 |
| Listed in CommandCenter | 2,592 |
| **Absent** | **4,153** |
| …but within 7 miles of a listed market — infill inside a rep's trade area | 2,483 |
| **Standalone and absent** | **1,670** |
| …with a tracked anchor store within 7 miles | **1,306** |

**1,306 is the real number.** The other 2,847 are either already covered or
are the next suburb over from a market a rep already owns, at the same 7-mile
geofence the store join, the basin collision test and `/gaps` all use.

## The list is three different problems

Sorted by population, the absent list opens with San Jose, Peoria AZ, Salinas
and Hesperia. None of those is an untapped opportunity — the CRM *dropped*
them between the 10/04 and 11/05 exports. Reporting them as new markets would
have been the single biggest error this audit could make, so every row carries
a class:

| Class | Anchored standalone | Means |
|---|---:|---|
| **A — never listed** | 60 | Absent from CommandCenter *and* from Market Finder. Genuinely unexplored. |
| **B — unlisted prospect** | 1,127 | Absent from the CRM; Market Finder already has it as Available. |
| **C — dropped** | 119 | Absent from this export, but Market Finder marks it Assigned/Active/Holding. The CRM listed it before. |

Class C is a reconciliation job, not a prospecting list: 77 markets our board
calls Active and 42 it calls Assigned have no row in the current export. The
largest are San Jose (990,054), Peoria AZ (194,338), Salinas (161,993),
Hesperia (100,141), Fayetteville AR (97,227) and Coral Gables (49,243).
Somebody should establish whether those territories were released, renamed, or
dropped by accident, because today the two systems disagree about who owns
them.

## Where the room actually is

| Population band | Markets | A | B | C |
|---|---:|---:|---:|---:|
| 50,000+ | 8 | 1 | 2 | 5 |
| 20,000–50,000 | 37 | 2 | 17 | 18 |
| 10,000–20,000 | 383 | 12 | 311 | 60 |
| 5,000–10,000 | 878 | 45 | 797 | 36 |

**The country is covered at the top and open at the bottom.** Only 8 standalone
markets above 50,000 are missing, and 5 of those are class C — markets we had
and lost. 878 of the 1,306, two thirds, are towns of 5,000–10,000. If the plan
is to grow by adding markets, the growth is small-town by arithmetic, not by
preference.

By state, the missing anchored markets are spread far more evenly than the
western analysis suggested: CA 81, TX 77, PA 77, OH 63, IL 60, NY 58, FL 54,
MO 54, MI 49, IN 47, IA 47, WI 47, TN 45. By dial window: Eastern 600,
Central 485, Pacific 127, Mountain 94.

## The 116 genuinely isolated markets

These are class A or B, anchored, and **40+ miles from anything CommandCenter
lists** — no collision with an existing rep under any reading of the trade
area, and no argument about who owns them:

| Market | Pop | Anchor | Miles to the nearest listed market |
|---|---:|---|---:|
| Caribou, ME | 7,427 | Hannaford 3.8mi | 170 |
| Presque Isle, ME | 8,736 | Walmart 1.2mi | 159 |
| Miles City, MT | 8,412 | Albertsons 0.7mi | 135 |
| Winnemucca, NV | 8,391 | Walmart 1.3mi | 123 |
| Pierre, SD | 14,008 | Walmart 0.6mi | 123 |
| Ironwood, MI | 5,004 | Super 1 Foods 0.9mi | 106 |
| Alpena, MI | 10,178 | IGA 1.0mi | 104 |
| Havre, MT | 9,333 | Walmart 2.8mi | 103 |
| Lewistown, MT | 6,028 | Albertsons 1.7mi | 99 |
| Colby, KS | 5,389 | Walmart 1.2mi | 98 |
| Page, AZ | 7,407 | Walmart 2.9mi | 96 |
| Lamar, CO | 7,629 | Walmart 1.0mi | 96 |
| Cody, WY | 10,121 | Albertsons 0.3mi | 91 |
| Rawlins, WY | 8,217 | City Market 0.8mi | 87 |
| Devils Lake, ND | 7,170 | Walmart 1.8mi | 84 |
| Cleveland, MS | 10,855 | Kroger 1.0mi | 80 |
| Massena, NY | 10,234 | Price Chopper 0.7mi | 78 |
| Spirit Lake, IA | 5,469 | Hy-Vee 0.5mi | 76 |

Filter `out/coverage.csv` on `class` starting `A`/`B` and
`nearest_listed_miles >= 40` for all 116.

## The never-listed markets worth a look first

Class A, standalone, anchored, largest first. These are absent from
CommandCenter *and* from Market Finder, so nobody has looked at them:

Four Corners FL (60,443, Publix 1.5mi) · Bridgeton NJ (26,836, Save-A-Lot
0.2mi) · Midway FL (20,745, Publix 3.3mi) · Westerly RI (18,528, Walmart
2.5mi) · Southbridge MA (17,806, Big Y 1.4mi) · Greenfield MA (17,662, Big Y
2.4mi) · Brunswick ME (16,928, Shaw's 1.6mi) · Palmer MA (12,372) · Webster MA
(12,300) · Nantucket MA (10,837, Stop & Shop 0.2mi) · Orono ME (10,699) ·
Canandaigua NY (10,542, Wegmans 1.6mi) · Exeter NH (10,138) · Hamburg NY
(9,762, Wegmans 4.3mi) · Monroe NY (9,466).

The concentration in New England is not a coincidence: Massachusetts, Maine,
New Hampshire and Rhode Island report most of their population through town
and CDP geographies that a city-name-based CRM import tends to miss entirely.

## Caveats, in the order they would bite

1. **231 of the 1,306 are CDPs**, flagged `cdp_not_a_municipality`. A
   census-designated place has no city hall and often no chamber. Two in the
   class A list are not markets at all — **Camp Pendleton Mainside CA** is a
   military base and **On Top of the World FL** is a retirement community.
   Filter on the flag before handing the list to anyone.
2. **930 of the 1,306 have a mainstream anchor** (Walmart, Kroger) as their
   best store. Only 152 have a warehouse club and 173 a dominant regional
   anchor. On the grocery-anchor model these are the weaker end.
3. **364 standalone markets have no tracked anchor** and are excluded from the
   headline. They are a mix of genuinely storeless towns and holes in the
   94-brand store dataset — Jungle Jim's and Kings Food Markets are cached
   empty right now, and Straub's and McCaffrey's are undercounted at one store
   each.
4. **The 5,000 floor is doing real work.** It excludes 8 of the 69 western
   markets the earlier analysis flagged as dropped, including Willcox AZ
   (3,236) and Bonners Ferry ID (2,615). If small towns are in scope, lower
   the floor and re-run; the pipeline takes a number.
5. **Population is ACS 2023 5-year**, which is a 2019–2023 average. It is the
   only source that covers all 32,000 places, but a fast-growing exurb reads
   low.
6. **Golden Glades CDP, FL (35,042) is unresolved** — it has ACS population
   but no 2024 Gazetteer record, so it has no coordinates and is absent from
   the audit entirely. Two other places were dropped for the same reason, both
   under 500 people.

## Data-quality findings for CommandCenter itself

Not what the audit was for, but it fell out of the join:

- **Two rows are neighbourhoods, not markets.** *Granada Hills CA* (carried at
  53,998) is a Los Angeles neighbourhood and *Corona Del Mar CA* is part of
  Newport Beach. Neither is a Census place, and both are already inside a
  listed market's trade area.
- **County population on city rows.** The export has San Jose at 1,729,879
  (Census: 990,054) and Riverside at 2,022,285. Any ranking built on the CRM's
  own population column is wrong at the top.
- **Four duplicate markets** under one normalized key, and **12 Canadian rows**
  in a US export (the Canada board is a separate instance with its own
  universe).
- **Status casing is still split** — 335 `ACTIVE` and 240 `Active`, 139
  `ASSIGNED` and 2,127 `Assigned` in the same file. Harmless once
  canonicalized, but it means two code paths upstream are writing the field.
- **Mojibake persists**: `La CaÃ±ada Flintridge` is in the live data,
  double-UTF-8-encoded.

## Method

Universe from the **Census ACS 2023 5-year table B01003** (population for all
32,325 places) joined to the **2024 TIGER Gazetteer** (coordinates) on GEOID,
with a name fallback for the five places whose ACS place code does not match,
and an alias for the ten city/county consolidations the Census names
differently (Louisville/Jefferson County, Augusta-Richmond County, Urban
Honolulu, Butte-Silver Bow). Markets join on a normalized key — accent-folded,
`saint`→`st` — identical to the one Market Finder uses. Distances are
haversine, bucketed on a half-degree grid. Anchors are the 18,560 stores in
the vendored OpenStreetMap dataset, joined at 7 miles and ranked warehouse
club first.

Reproduce: `python3 -I build_coverage.py data/<export>.csv`

Every count above reconciles against the planning probe: the universe differs
by exactly the 54 Puerto Rican places excluded by scope plus the 4
Massachusetts towns recovered by name, infill matches exactly, and class C
accounts for all 69 western dropped markets (59 here, 10 below the 5,000
floor or not Census places).
