# REAL BUG: drivers/scsi/qla2xxx/qla_mbx.c:245 qla2x00_get_sp()

**Confidence**: MEDIUM | **Counter**: `vha->vref_count.counter`

## Reasoning

| L241 → done | return sp (sp alloc succeeds) | YES | NO (intentional transfer) | ✅ | `sp->vha = vha` transfers ownership; reference released in sp lifetime. |

## Full Response

```
| Line | Return Type      | GET Done? | PUT Done? | Balanced? | Notes                                                                 |
|------|------------------|-----------|-----------|-----------|-----------------------------------------------------------------------|
| L232 | early return NULL | YES       | NO        | ❌ LEAK    | Returns without `QLA_VHA_MARK_NOT_BUSY`. QLA_VHA_MARK_BUSY assumed to always incref. |
| L237 → done | return NULL (sp alloc fails) | YES | YES | ✅ | `goto done` → `if (!sp) QLA_VHA_MARK_NOT_BUSY(vha)` releases ref. |
| L241 → done | return sp (sp alloc succeeds) | YES | NO (intentional transfer) | ✅ | `sp->vha = vha` transfers ownership; reference released in sp lifetime. |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
The early return path after `qla_vha_mark_busy(vha)` fails to call `QLA_VHA_MARK_NOT_BUSY(vha)`, leaking the reference if `qla_vha_mark_busy` increments `vha->vref_count.counter` unconditionally (as smatch detects).
```
