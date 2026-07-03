# REAL BUG: block/blk-zoned.c:1574 blk_zone_wplug_handle_native_zone_append()

**Confidence**: HIGH | **Counter**: `$->ref.refs.counter`

## Reasoning

| ~1555 (path with bio_list not empty) | function exit (void) | YES | YES (disk_zone_wplug_abort puts, mark_dead puts, then disk_put_zone_wplug puts) | ❌ EXCESS PUT | abort drops a ref, mark_dead drops another, final put drops a third → triple put on a single get. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~1547 (early return) | early return if !zwplug | NO (get returned NULL) | N/A | ✅ | no ref taken |
| ~1558 (path with bio_list empty) | function exit (void) | YES (disk_get_zone_wplug succeeded) | YES (disk_mark_zone_wplug_dead puts, then disk_put_zone_wplug puts) | ❌ EXCESS PUT | mark_dead drops ref (hash ref), final put drops caller’s ref again → double put. If mark_dead does not put because already dead, still caller put is one put for one get but the warning says excess put, implying at least one extra put occurred. |
| ~1555 (path with bio_list not empty) | function exit (void) | YES | YES (disk_zone_wplug_abort puts, mark_dead puts, then disk_put_zone_wplug puts) | ❌ EXCESS PUT | abort drops a ref, mark_dead drops another, final put drops a third → triple put on a single get. |

**PRE-VERDICT CHECKLIST**:
1. "Held for device lifetime"? Not relevant.
2. "Ownership transferred"? No transfer, callers own their get reference.
3. Unconditional GET? `disk_get_zone_wplug` is conditional, but once it succeeds ref is held.
4. goto out between GET and PUT? Not applicable. The function has no goto, all paths lead to excess puts.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`disk_get_zone_wplug` returns a plug with a single reference; the function then calls `disk_zone_wplug_abort` (when bio_list not empty), `disk_mark_zone_wplug_dead`, and `disk_put_zone_wplug`, each of which drops a reference (contracts confirm), leading to 2‑3 puts for 1 get and an excess put on `ref.refs.counter`.
```
