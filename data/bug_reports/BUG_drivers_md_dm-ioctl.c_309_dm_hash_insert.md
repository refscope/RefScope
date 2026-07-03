# REAL BUG: drivers/md/dm-ioctl.c:309 dm_hash_insert()

**Confidence**: HIGH | **Counter**: `hc->md->holders.counter`

## Reasoning

| L309 (success path) | return 0 | YES (dm_get(md) on new md) | NO (reference held by cell) | ⚠️ (balanced externally) | dm_get for the newly inserted cell; not leaked here |

## Full Response

```
| Line | Return Type | GET Done? (dm_get) | PUT Done? (dm_put) | Balanced? | Notes |
|------|-------------|---------------------|---------------------|-----------|-------|
| L272 (if !cell) | error return -ENOMEM | NO (alloc failed) | NO | ✅ | no refs held |
| L288 (if hc after __get_name_cell) → bad → -EBUSY | error return | NO (no dm_get on hc->md) | YES (dm_put(hc->md)) | ❌ EXCESS PUT | puts a reference that belongs to the existing cell, not acquired in this path |
| L296 (if uuid and __get_uuid_cell) → bad → -EBUSY | error return | NO (no dm_get on hc->md) | YES (dm_put(hc->md)) | ❌ EXCESS PUT | same pattern as above |
| L309 (success path) | return 0 | YES (dm_get(md) on new md) | NO (reference held by cell) | ⚠️ (balanced externally) | dm_get for the newly inserted cell; not leaked here |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
dm_hash_insert() erroneously calls dm_put(hc->md) when a name or UUID already exists, dropping a reference that it never acquired. hc->md belongs to the existing cell, and this excess put underflows the refcount.
```
