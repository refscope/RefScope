# REAL BUG: fs/nfsd/nfscache.c:549 nfsd_cache_lookup()

**Confidence**: HIGH | **Counter**: `nn->num_drc_entries.counter`

## Reasoning

| L496 → found_entry | goto found_entry → out_trace/out_unlock | NO | YES (inside `nfsd_reply_cache_free_locked`) | ❌ | free of uninserted `rp`; counter not incremented |

## Full Response

```
| Line | Return Type | GET Done? (atomic_inc) | PUT Done? | Balanced? | Notes |
|------|-------------|------------------------|-----------|-----------|-------|
| L478 | RC_NOCACHE, goto out | NO | N/A | ✅ | early return, no inc |
| L488 | alloc fail, goto out | NO | N/A | ✅ | rp is NULL, no inc |
| L493–L510 | cache miss (found == rp), goto out | YES (L509) | NO (here), but deferred by cache lifecycle | ✅ (eventual) | inc when inserting; put when pruned/freed later |
| L496 → found_entry | goto found_entry → out_trace/out_unlock | NO | YES (inside `nfsd_reply_cache_free_locked`) | ❌ | free of uninserted `rp`; counter not incremented |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the `found_entry` path (duplicate cache entry), `nfsd_reply_cache_free_locked` frees the pre-allocated `rp` without it ever being inserted or having its counter incremented (`atomic_inc` only occurs on successful insert). Since `nfsd_reply_cache_free_locked` internally decrements `nn->num_drc_entries`, the counter gets an extra decrement, producing the “refcount excess put” warning at line 549.
```
