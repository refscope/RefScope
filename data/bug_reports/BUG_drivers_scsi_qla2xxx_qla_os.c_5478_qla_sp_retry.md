# REAL BUG: drivers/scsi/qla2xxx/qla_os.c:5478 qla_sp_retry()

**Confidence**: HIGH | **Counter**: `$->cmd_kref.refcount.refs.counter`

## Reasoning

UCCESS) | calls `qla24xx_sp_unmap`, then implicit return | NO (conditional get did **not** happen) | YES (unconditional put via `qla24xx_sp_unmap`) | ❌ EXCESS PUT | `qla2x00_start_sp` failed, so no kref_get(s) occurred; calling unmap releases references that were never taken → refcount underflow |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L5468–L5479 (rval == QLA_SUCCESS) | implicit return (void) | YES (conditional on success per contract) | NO | ⚠️  (ref held, possibly released later) | Success path holds extra reference(s); not the focus of this warning |
| L5470–L5478 (rval != QLA_SUCCESS) | calls `qla24xx_sp_unmap`, then implicit return | NO (conditional get did **not** happen) | YES (unconditional put via `qla24xx_sp_unmap`) | ❌ EXCESS PUT | `qla2x00_start_sp` failed, so no kref_get(s) occurred; calling unmap releases references that were never taken → refcount underflow |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On error from `qla2x00_start_sp` (rval != QLA_SUCCESS) the conditional get(s) did not occur, but `qla24xx_sp_unmap` unconditionally performs kref_put(s), causing an excess put on `cmd_kref`. The function must not call `qla24xx_sp_unmap` when the start failed.
```
