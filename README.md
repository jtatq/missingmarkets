# missingmarkets

An independent audit of **what the CommandCenter territory list is missing**.

This is deliberately a separate project from `market-finder`. Every market
list we have is downstream of CommandCenter: Market Finder's universe was
seeded from CRM exports and grown by hand, so asking it what we are missing is
circular — it can only report markets it already knows. This builds the
universe from the Census instead, which has never seen our CRM, and subtracts.

Nothing here reads, writes, imports or deploys anything in `market-finder`.
Two of its files are vendored into `data/vendor/` as read-only inputs and are
documented there.

## The answer, as of the 2026-11-05 export

| | |
|---|---|
| US places with 5,000+ residents (Census) | 6,745 |
| Listed in CommandCenter | 2,592 (**38%**) |
| Absent from it | 4,153 |
| …of which infill inside a listed market's 7-mile trade area | 2,483 |
| **Standalone markets CommandCenter has no row for** | **1,670** |
| …with a tracked anchor store within 7 miles | **1,306** |

Read `out/findings.md` for the analysis. `out/coverage.csv` is the data,
one row per absent market, built to open straight in Excel.

**The list is not one thing.** Every row is classed, because sorted by
population the absent list opens with San Jose and Salinas — markets the CRM
*dropped*, not markets it never had:

- **A — never listed** (60 anchored standalone): absent from CommandCenter
  *and* from Market Finder. Genuinely unexplored.
- **B — unlisted prospect** (1,127): absent from the CRM, known to Market
  Finder as Available.
- **C — dropped** (119): absent from this export, but Market Finder has it as
  Assigned/Active/Holding, so the CRM listed it before. Reconciliation, not
  prospecting.

## Running it

```bash
# 1. the universe (needs a free Census key; never committed)
CENSUS_KEY=... python3 -I fetch_places.py data/places.json

# 2. the audit — point it at a CommandCenter export you dropped in data/
python3 -I build_coverage.py data/commandcenter-territories-YYYY-MM-DD.csv
```

`data/places.json` is committed, so step 2 works without a Census key until
you want fresher population figures. Step 1 takes about a minute; step 2 runs
in a couple of seconds.

The `-I` is deliberate: the CRM export is untrusted input, so the scripts run
isolated from `PYTHONPATH` and the user site, and put their own directory back
on the path explicitly.

## Layout

```
fetch_places.py     Census ACS 5-year B01003 + TIGER Gazetteer -> data/places.json
load_crm.py         reads a CommandCenter export; repairs mojibake and status casing
build_coverage.py   the audit -> out/coverage.csv, out/coverage.json
mc_util.py          key(), tz_for(), haversine, GridIndex — copies, not imports
data/vendor/        read-only inputs borrowed from market-finder (see its README note)
out/                the deliverables
```

## Scope rules

Set deliberately; written down so they are not quietly re-litigated.

- **Population floor 5,000**, taken from the Census rather than the CRM. The
  CRM puts county population on city rows (it has San Jose at 1,729,879;
  Census says 990,054), so its own numbers cannot be ranked on.
- **Anchor required for the headline list.** A tracked grocery/club store
  within 7 miles — the same geofence the store join, basin collision and
  `/gaps` use. The 364 standalone markets with no anchor are still in the CSV,
  flagged `no_anchor`.
- **CDPs flagged, not dropped** (`cdp_not_a_municipality`). A census-designated
  place has no city hall and often no chamber. 231 of the 1,306 are CDPs, and
  a few are not markets at all — Camp Pendleton Mainside is a military base,
  On Top of the World is a retirement community. Filter on the flag.
- **Puerto Rico and the island areas excluded**; AK and HI kept but flagged.
