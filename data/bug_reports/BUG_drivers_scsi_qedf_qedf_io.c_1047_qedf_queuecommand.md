# REAL BUG: drivers/scsi/qedf/qedf_io.c:1047 qedf_queuecommand()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L1047 (post error) | `return rc` (post io req error) | YES | YES (same double‑put) | ❌ EXCESS PUT | identical over‑put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L950 | `return 0` (SG count) | NO (before alloc) | N/A | ✅ | |
| L960 | `return 0` (unloading/stop) | NO | N/A | ✅ | |
| L969 | `return 0` (no MSI‑X) | NO | N/A | ✅ | |
| L979 | `return 0` (chkready fail) | NO | N/A | ✅ | |
| L986 | `goto exit_qcmd` (drain active) | NO | N/A | ✅ | |
| L993 | `goto exit_qcmd` (link down) | NO | N/A | ✅ | |
| L1006 | `goto exit_qcmd` (session not ready) | NO | N/A | ✅ | |
| L1021 | `goto exit_qcmd` (retry delay active) | NO | N/A | ✅ | (`atomic_dec` done) |
| L1030 | `goto exit_qcmd` (alloc fails) | NO | N/A | ✅ | |
| L1047 (success) | `return rc` (post io req success) | YES (io_req from `qedf_alloc_cmd`) | YES (via `qedf_post_io_req`, contract: **unconditional double‑kref_put**) | ❌ EXCESS PUT | one get, two puts → refcount goes negative |
| L1047 (post error) | `return rc` (post io req error) | YES | YES (same double‑put) | ❌ EXCESS PUT | identical over‑put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`qedf_alloc_cmd` gives exactly one reference (kref_init), but `qedf_post_io_req` performs two unconditional kref_puts, producing an excess put on every path where `io_req` is successfully allocated and posted.
```
