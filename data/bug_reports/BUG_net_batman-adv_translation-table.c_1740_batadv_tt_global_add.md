# REAL BUG: net/batman-adv/translation-table.c:1740 batadv_tt_global_add()

**Confidence**: HIGH | **Counter**: `$->orig_list_count.counter`

## Reasoning

70) | ❌ | second del on empty list → orig_list_count underflow |
| L1670 | fallthrough → add_orig_entry (common->flags !TEMP, ROAM set) | YES (L1680) | YES (once at L1670) | ✅ | single del → add |

**

## Full Response

```
| Line | Return Type | GET Done? (add) | PUT Done? (del) | Balanced? | Notes |
|------|-------------|-----------------|-----------------|-----------|-------|
| L1595 | return true (backbone) | N/A | N/A | ✅ | early return |
| L1605 | goto out (TEMP+local) | N/A | N/A | ✅ | no global entry modification |
| L1608 | goto out (alloc fail) | N/A | N/A | ✅ | no global entry created |
| L1628 | goto out_remove (hash fail) | N/A | N/A | ✅ | new entry created but no orig list ops |
| L1645 | goto out (flags & TEMP, common->flags !TEMP) | N/A | N/A | ✅ | no del/add |
| L1645 | goto out_remove (flags & TEMP, common->flags TEMP, has_orig) | N/A | N/A | ✅ | no del (goes to out_remove) |
| L1645 | goto add_orig_entry (flags & TEMP, common->flags TEMP, !has_orig) | YES (L1680) | YES (once at L1645) | ✅ | single del → add |
| L1660 | fallthrough → add_orig_entry (common->flags TEMP, ROAM not set) | YES (L1680) | YES (once at L1660) | ✅ | single del → add |
| L1660+L1670 | fallthrough → add_orig_entry (common->flags TEMP **and** ROAM set) | YES (L1680) | **YES (twice)** (L1660, L1670) | ❌ | second del on empty list → orig_list_count underflow |
| L1670 | fallthrough → add_orig_entry (common->flags !TEMP, ROAM set) | YES (L1680) | YES (once at L1670) | ✅ | single del → add |

**VERDICT: REAL_BUG**

**CONFIDENCE: HIGH**

When a non‑temporary global addition replaces an existing temporary entry and the ROAM flag is set, `batadv_tt_global_del_orig_list()` is called twice (once for TEMP cleanup, once for ROAM cleanup) without an intervening `orig_entry_add`, causing a refcount underflow on `orig_list_count` at the second deletion.
```
