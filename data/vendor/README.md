# Vendored inputs

Two files copied once from the `market-finder` repo. They are **inputs**, not
dependencies: nothing here imports market-finder code, and this project never
writes back to it.

| File | From | Used for |
|---|---|---|
| `stores.json` | `deploy/stores.json`, generated 2026-10-04 | the anchor join. 18,560 stores across 94 chains in 5 tiers, from OpenStreetMap via Overpass (ODbL). |
| `territories-available.json` | `deploy/territories-available.json`, exported 2026-10-04 | **classification only** — telling a market the CRM never listed from one it dropped. Never used to build the universe; that would reintroduce exactly the circularity this project exists to avoid. |

Why `stores.json` is vendored rather than re-fetched: Overpass is hostile to
national queries. A full 94-brand refetch takes hours, 504s under any
parallelism, and caches an empty result as success. Re-deriving it here would
buy independence we do not need — the store data is OpenStreetMap's, not
CommandCenter's, so it cannot bias an audit of CommandCenter. Refetching is an
option later, not a blocker.

To refresh either file, copy a newer one in and re-run `build_coverage.py`.
The audit prints the generation dates it used.
