# REAL BUG: block/blk-zoned.c:836 disk_zone_wplug_sync_wp_offset()

**Confidence**: HIGH | **Counter**: `$->ref.refs.counter`

## Reasoning

| L835 (zwplug != NULL, NEED_WP_UPDATE not set) | return wp_offset | YES | YES (disk_put_zone_wplug once) | ✅ | Single put matches get. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L835 (zwplug == NULL) | return wp_offset | NO (disk_get_zone_wplug returned NULL) | N/A | ✅ | No reference held. |
| L835 (zwplug != NULL, NEED_WP_UPDATE set) | return wp_offset | YES (disk_get_zone_wplug returned non‑NULL) | YES (disk_zone_wplug_set_wp_offset PUT + disk_put_zone_wplug PUT) | ❌ Double put — refcount underflow | path calls two PUTs for one GET. |
| L835 (zwplug != NULL, NEED_WP_UPDATE not set) | return wp_offset | YES | YES (disk_put_zone_wplug once) | ✅ | Single put matches get. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
When BLK_ZONE_WPLUG_NEED_WP_UPDATE is set, `disk_zone_wplug_set_wp_offset()` (a PUT per contract) is called, then `disk_put_zone_wplug()` is called again, resulting in a double decrement of the reference count.
```
