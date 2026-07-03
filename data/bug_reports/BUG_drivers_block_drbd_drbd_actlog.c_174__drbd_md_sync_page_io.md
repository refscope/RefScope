# REAL BUG: drivers/block/drbd/drbd_actlog.c:174 _drbd_md_sync_page_io()

**Confidence**: HIGH | **Counter**: `$->__bi_cnt.counter`

## Reasoning

_done_or_force_detached returns early due to force-detach **without** calling drbd_md_endio | Return through out path (L174 area) | YES (ref=2) | NO (endio never called) | YES (out: bio_put drops alloc ref → ref=1 leaked) | ❌ LEAK | bio_get extra ref never released; bio remains with refcount 1 |

## Full Response

```
| Line | Return Type | GET Done? (bio_get) | PUT Done? (endio put) | PUT Done? (out bio_put) | Balanced? | Notes |
|------|-------------|---------------------|------------------------|-------------------------|-----------|-------|
| L144 (≈) | `goto out` — bio_add_page failed | NO (before bio_get) | N/A | YES (out: bio_put releases alloc ref) | ✅ | Alloc ref (ref=1) safely freed |
| L155 (≈) | `goto out` — get_ldev_if_state failed | NO (before bio_get) | N/A | YES (out: bio_put) | ✅ | Same as above, no extra ref held |
| L166… after bio_get, via submit_bio / bio_io_error, then wait normally (endio runs) | Normal success/error return through out | YES (bio_get increments ref to 2) | YES (drbd_md_endio called during IO completion, drops extra ref) | YES (out: bio_put drops alloc ref) | ✅ | Extra ref consumed by completion handler |
| L166… after bio_get, but wait_until_done_or_force_detached returns early due to force-detach **without** calling drbd_md_endio | Return through out path (L174 area) | YES (ref=2) | NO (endio never called) | YES (out: bio_put drops alloc ref → ref=1 leaked) | ❌ LEAK | bio_get extra ref never released; bio remains with refcount 1 |

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  

`bio_get` at L166 takes an extra reference intended for the I/O completion handler (`drbd_md_endio`). If `wait_until_done_or_force_detached` returns early due to force-detach without the completion handler having been called, the endio never performs its `bio_put`, so the extra reference is leaked. The `out:` label’s `bio_put` only releases the initial alloc reference, leaving the bio behind with refcount 1 → refcount leak.
```
