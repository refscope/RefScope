# REAL BUG: drivers/scsi/qla2xxx/qla_init.c:1205 qla24xx_async_gnl()

**Confidence**: HIGH | **Counter**: `$->cmd_kref.refcount.refs.counter`

## Reasoning

L1205 | error / goto done_free_sp | YES (sp allocated, init ref=1; start_sp failed → no conditional gets from start_sp assumed) | YES (qla24xx_async_gnl_sp_done does 2 unconditional kref_put) | ❌ EXCESS PUT | Only 1 initial ref, but done does 2 puts → second put on already zero/freed refcount |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1158 | early return (success) | NO (no sp allocated) | N/A | ✅ | |
| L1166 | goto done (sp==NULL) | NO (sp NULL, no ref taken) | N/A | ✅ | |
| L1193 | success return after start_sp | YES (init ref + conditional gets from start_sp) | NO (put deferred to async callback) | ✅ (ref held for async lifecycle) | no immediate put, but designed for later release via done callback; not a leak |
| L1191 → L1201 (done_free_sp) → L1205 | error / goto done_free_sp | YES (sp allocated, init ref=1; start_sp failed → no conditional gets from start_sp assumed) | YES (qla24xx_async_gnl_sp_done does 2 unconditional kref_put) | ❌ EXCESS PUT | Only 1 initial ref, but done does 2 puts → second put on already zero/freed refcount |

**VERDICT: REAL_BUG**   
**CONFIDENCE: HIGH**   
`qla24xx_async_gnl_sp_done` performs two unconditional `kref_put` (contract), but the error path after `qla2x00_start_sp` failure likely holds only the initial reference (1). Manually calling `qla24xx_async_gnl_sp_done` on the error path therefore does an excess put, leading to a refcount underflow/use‑after‑free.
```
