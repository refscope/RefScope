# REAL BUG: fs/afs/cell.c:400 afs_lookup_cell()

**Confidence**: HIGH | **Counter**: `$->active.counter`

## Reasoning

| ~402 | error (candidate alloc fail already covered) | — | — | ✅ | — |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~290 | error (candidate alloc fail) | NO | NO | ✅ | IS_ERR candidate, return candidate directly — no use/unuse |
| ~385 | success (found cell via afs_find_cell, state ACTIVE, DNS good) | NO | NO | ✅ | Cell returned to caller with base ref; no active use taken |
| ~385 | success (insertion path, new cell) | YES (L315) | NO | ✅ (transfer) | Active ref taken at L315, returned to caller — caller owns it |
| ~385 | success (cell_already_exists, non-PRELOAD) | YES (L339) | NO | ✅ (transfer) | Active ref taken at L339, transferred to caller |
| ~385 | success (early found → no_wait, active) | NO | NO | ✅ | No use call |
| ~400 | error (found cell, wait_for_cell → state DEAD) | NO | YES | ❌ EXCESS PUT | `goto error` from L354, unuse at L400 without prior use |
| ~400 | error (found cell, wait_for_cell → DNS error) | NO | YES | ❌ EXCESS PUT | `goto error` from L357+, unuse at L400 without use |
| ~400 | error (found cell, lookup_cell → wait_for_cell → dead/dns error) | NO | YES | ❌ EXCESS PUT | Same as above, reached via `goto lookup_cell` |
| ~400 | error (insertion path, wait_for_cell → dead/dns error) | YES (L315) | YES (L400) | ✅ | Use at L315, unuse at L400 — balanced |
| ~400 | error (cell_already_exists, non-PRELOAD → wait_for_cell → dead/dns error) | YES (L339) | YES (L400) | ✅ | Use at L339, unuse at L400 — balanced |
| ~402 | error (cell_already_exists PRELOAD) | NO | NO (error_noput) | ✅ | No use, no unuse — EEXIST path |
| ~402 | error (candidate alloc fail already covered) | — | — | ✅ | — |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`afs_unuse_cell(cell, ...)` at `error:` is called unconditionally, but the early-found-via-`afs_find_cell` paths (go to `wait_for_cell`, `lookup_cell`, `no_wait` then hit dead state or DNS error) never call `afs_use_cell`, causing an excess active counter decrement.
```
