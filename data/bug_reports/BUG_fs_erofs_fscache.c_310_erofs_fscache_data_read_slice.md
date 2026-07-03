# REAL BUG: fs/erofs/fscache.c:310 erofs_fscache_data_read_slice()

**Confidence**: HIGH | **Counter**: `$->ref.refs.counter`

## Reasoning

| **L310: `return ret` after `erofs_fscache_read_io_async`** | error/success | **YES** (async GET) | **NO** | ❌ **LEAK** | async get not released; `erofs_fscache_req_io_put` only drops alloc ref |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L248-ish: `return ret` from `erofs_map_blocks` error | error | NO | N/A | ✅ | Before any get |
| L265-ish: `return PTR_ERR(src)` in meta path | error | NO | N/A | ✅ | Before any get |
| L271-ish: `return -EFAULT` in meta copy fault | error | NO | N/A | ✅ | Before any get |
| L275-ish: `return 0` in meta success | success | NO | N/A | ✅ | Before any get |
| L290-ish: `return 0` in unmapped path | success | NO | N/A | ✅ | Before any get |
| L295-ish: `return ret` from `erofs_map_dev` error | error | NO | N/A | ✅ | Before any get |
| L302-ish: `return -ENOMEM` when `!io` | error | NO (alloc failed) | N/A | ✅ | |
| **L310: `return ret` after `erofs_fscache_read_io_async`** | error/success | **YES** (async GET) | **NO** | ❌ **LEAK** | async get not released; `erofs_fscache_req_io_put` only drops alloc ref |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`erofs_fscache_read_io_async` unconditionally takes a reference, but on error it never schedules the callback that would release it; the caller has no put for this extra ref — a leak when the function returns `ret`.
```
