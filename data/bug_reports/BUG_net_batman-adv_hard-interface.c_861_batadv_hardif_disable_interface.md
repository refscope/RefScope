# REAL BUG: net/batman-adv/hard-interface.c:861 batadv_hardif_disable_interface()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L864 (end, hard_iface is primary) | normal exit | YES (batadv_primary_if_get_selected) | YES (batadv_hardif_put at L864) BUT batadv_primary_if_select already put the same ref | ❌ EXCESS PUT | select puts the old primary_if internally, causing double-put when the local put executes |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L824 (goto out) | early out | NO (primary_if=NULL) | N/A (null safe) | ✅ | primary_if never obtained, batadv_hardif_put(NULL) is safe |
| L864 (end, hard_iface not primary) | normal exit | YES (batadv_primary_if_get_selected) | YES (batadv_hardif_put at L864) | ✅ | ref acquired and released once |
| L864 (end, hard_iface is primary) | normal exit | YES (batadv_primary_if_get_selected) | YES (batadv_hardif_put at L864) BUT batadv_primary_if_select already put the same ref | ❌ EXCESS PUT | select puts the old primary_if internally, causing double-put when the local put executes |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
When the disabled interface is the current primary, batadv_primary_if_select drops the reference of the old primary (the get_selected result) inside, but the function later puts it again, causing an excess put.
```
