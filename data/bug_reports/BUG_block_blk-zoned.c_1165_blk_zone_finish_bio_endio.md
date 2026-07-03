# REAL BUG: block/blk-zoned.c:1165 blk_zone_finish_bio_endio()

**Confidence**: HIGH | **Counter**: `zwplug->ref.refs.counter`

## Reasoning

g incremented refcount) | YES (explicit disk_put_zone_wplug at L1156) + possible internal put from disk_zone_wplug_set_wp_offset at L1154 | ❌ Excess put | Contract for set_wp_offset says it can put the wplug; unconditional put after it creates a double-put on paths where the internal put occurs. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1160 (NULL path) | implicit return | NO (disk_get_zone_wplug returned NULL) | N/A | ✅ | No get, no put. |
| L1160 (non‑NULL path) | implicit return | YES (disk_get_zone_wplug incremented refcount) | YES (explicit disk_put_zone_wplug at L1156) + possible internal put from disk_zone_wplug_set_wp_offset at L1154 | ❌ Excess put | Contract for set_wp_offset says it can put the wplug; unconditional put after it creates a double-put on paths where the internal put occurs. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`disk_get_zone_wplug` increments refcount; `disk_zone_wplug_set_wp_offset` can internally put the wplug (per contract), and the subsequent unconditional `disk_put_zone_wplug` causes an excess put.
```
