# REAL BUG: fs/erofs/fscache.c:238 erofs_fscache_meta_read_folio()

**Confidence**: HIGH | **Counter**: `$->ref.refs.counter`

## Reasoning

- **goto out** – Not relevant; the leak is on the post‑async error path.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L219 (return ret) | error (req NULL) | NO (erofs_fscache_req_alloc failed) | N/A | ✅ | No req object allocated |
| L225 goto out (io NULL) | error | YES (req ref=1 from req_alloc) | YES (erofs_fscache_req_put at L235) | ✅ | io_alloc failed, no extra inc on req |
| L233→L236 (ret==0) | success | YES (req_alloc ref=1, io_alloc inc→2, async inc→3 on req; io ref=2) | YES (io_put + req_put, but async still holds its refs) | ✅ (async will release later) | Async operation owns the remaining refs for its lifetime |
| L233→L236 (ret<0) | error | YES (same unconditional gets as above, req ref=3, io ref=2) | YES (io_put → io ref=1, req_put → req ref=2; but async inc not released) | ❌ **LEAK** | erofs_fscache_read_io_async took refs unconditionally, but on error the async work is not scheduled and those extra refs are never released |

---

**Pre‑verdict checklist (Lesson 2, 3, 4, 5)**  
- **“Held for device lifetime”?** – No, only async success path holds refs; error path leaves them dangling.  
- **Ownership transferred?** – No documented cleanup on the error path that releases the extra refs taken by async.  
- **Unconditional GET** – `erofs_fscache_read_io_async` is unconditional (`→refcount_inc(get),refcount_inc(get)`), always increments. The caller MUST release on error.  
- **goto out** – Not relevant; the leak is on the post‑async error path.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`erofs_fscache_read_io_async` unconditionally bumps the req and io refcounts; on failure (ret<0) those extra references are never dropped, causing a refcount leak.
```
