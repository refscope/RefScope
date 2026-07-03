# REAL BUG: drivers/md/dm-pcache/cache_req.c:789 cache_write()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

| L785 | success (return 0 after loop) | YES (final key from last iteration) | NO | ✅ (transferred) | after insert/append, reference held by tree; no explicit put needed |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L760 | error (cache_data_alloc fail) → L789 (err) | YES (cache_key_alloc at L753) | YES (cache_key_put at L761) | ✅ | alloc gave ref=1, put releases it |
| L767 | error (cache_copy_from_req_bio fail) → L789 (err) | YES | YES (cache_key_put at L768) | ✅ | put after seg put |
| L774 | error (cache_key_append fail) → L787 (unlock) → L789 (err) | YES | YES (cache_key_delete at L775) | ❌ EXCESS PUT | key already inserted via `cache_key_insert` (L773); reference transferred to tree; this put will underflow on tree cleanup |
| L785 | success (return 0 after loop) | YES (final key from last iteration) | NO | ✅ (transferred) | after insert/append, reference held by tree; no explicit put needed |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`cache_key_alloc` creates a key with refcount=1; after `cache_key_insert` (L773), ownership transfers to the tree. The error path at L774–L775 calls `cache_key_delete(key)`, which does an unconditional put, causing a double-release when the tree later removes the node.
```
