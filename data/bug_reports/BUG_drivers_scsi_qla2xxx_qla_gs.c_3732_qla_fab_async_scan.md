# REAL BUG: drivers/scsi/qla2xxx/qla_gs.c:3732 qla_fab_async_scan()

**Confidence**: HIGH | **Counter**: `sp->cmd_kref.refcount.refs.counter`

## Reasoning

| L3680 | success     | YES (ref to be handed off to async) | NO (deliberate) | ✅ | sp ownership transferred; callback will put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3525 | error       | YES (sp passed with ref) | NO   | ❌ LEAK | !online quick return bypasses any kref_put; caller's reference leaked |
| L3533 | goto done_free_sp | YES (sp passed with ref) | YES (kref_put) | ✅ | scan active → done_free_sp calls kref_put |
| L3554 | error       | NO (get_sp failed, sp=NULL) | N/A  | ✅ | sp NULL, no ref to release |
| L3565 | error       | YES (initial ref from get_sp) | YES (qla2x00_rel_sp) | ✅ | qla2x00_rel_sp releases the INIT ref |
| L3575 | error       | YES (initial ref) | YES (qla2x00_rel_sp) | ✅ | |
| L3593 | goto done_free_sp | YES (sp non‑NULL) | YES (kref_put) | ✅ | default/WARN path |
| L3601 | error       | NO (sp is NULL) | N/A  | ✅ | no ref held |
| L3610 | goto done_free_sp | YES | YES (kref_put) | ✅ | req/rsp not setup |
| L3677 | goto done_free_sp | YES | YES (kref_put) | ✅ | start_sp failure |
| L3680 | success     | YES (ref to be handed off to async) | NO (deliberate) | ✅ | sp ownership transferred; callback will put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Early return at L3525 when !vha->flags.online leaks the reference of the passed‑in `sp` because it does not call `kref_put` (or `qla2x00_rel_sp`), unlike every other error path that releases the sp.
```
