# REAL BUG: fs/btrfs/zoned.c:2971 btrfs_zone_finish_one_bg()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| L2973 | return after put | YES (loop final min_bg) | YES (L2971 explicit put) | ❌ EXCESS | btrfs_zone_finish() internally releases a reference on min_bg, causing the subsequent explicit put to underflow the refcount. Smatch detected refcount excess put at L2971, confirming a double-put. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2969 | return 0 (min_bg NULL) | NO (no candidate) | N/A | ✅ | No block group selected, no gets/puts. |
| L2973 | return after put | YES (loop final min_bg) | YES (L2971 explicit put) | ❌ EXCESS | btrfs_zone_finish() internally releases a reference on min_bg, causing the subsequent explicit put to underflow the refcount. Smatch detected refcount excess put at L2971, confirming a double-put. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
btrfs_zone_finish() releases a reference on min_bg, so the explicit put at L2971 triggers a refcount underflow (excess put).
```
