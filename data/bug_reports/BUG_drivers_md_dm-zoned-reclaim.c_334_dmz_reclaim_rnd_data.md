# REAL BUG: drivers/md/dm-zoned-reclaim.c:334 dmz_reclaim_rnd_data()

**Confidence**: HIGH | **Counter**: `$->nr_reserved_seq_zones.counter`

## Reasoning

| L323 (error, szone allocated with DMZ_ALLOC_RND) | ret≠0 | **NO** (random zone, no seq get) | **YES** (dmz_free_zone unconditionally decrements seq counter) | ❌ EXCESS PUT | causes refcount underflow on `nr_reserved_seq_zones` |

## Full Response

```
| Line | Return Type | GET Done? (seq counter) | PUT Done? (seq counter) | Balanced? | Notes |
|------|-------------|-------------------------|-------------------------|-----------|-------|
| L296 | -ENOSPC     | NO (szone NULL)         | N/A                     | ✅         | alloc failed, no ref taken |
| L323 (success, dzone freed) | 0 | YES if szone was seq; else NO | NO on szone (ref held); PUT on dzone (irrelevant) | ✅ (szone not freed, seq counter untouched if rnd) | szone mapped, dzone freed |
| L323 (error, szone allocated with DMZ_ALLOC_SEQ) | ret≠0 | YES                     | YES (dmz_free_zone)     | ✅         | balanced put |
| L323 (error, szone allocated with DMZ_ALLOC_RND) | ret≠0 | **NO** (random zone, no seq get) | **YES** (dmz_free_zone unconditionally decrements seq counter) | ❌ EXCESS PUT | causes refcount underflow on `nr_reserved_seq_zones` |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

dmz_reclaim_rnd_data() falls back to a random zone when sequential allocation fails, but the error path always calls dmz_free_zone() on szone, which decrements the sequential reserve counter even when the zone is random (no prior increment). This triggers an excess put on the warning line.
```
