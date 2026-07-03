# REAL BUG: drivers/scsi/qedf/qedf_main.c:863 qedf_eh_abort()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| qedf_initiate_abts success → fallthrough to drop → out | return rc | YES | YES at out | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? (io_req) | PUT Done? (io_req) | Balanced? | Notes |
|------|-------------|---------------------|---------------------|-----------|-------|
| stale rport (goto out)                   | return rc | NO (before get) | N/A | ✅ | got_ref=0 |
| io_req NULL → goto drop_rdata_kref       | return rc | NO (before get) | N/A | ✅ | got_ref=0 |
| kref_get_unless_zero fails (rval=0) → drop | return rc | NO | NO (got_ref=0) | ✅ | |
| kref_get_unless_zero ok but sc_cmd mismatch → drop | return rc | YES | YES at out | ✅ | got_ref=1, put at out |
| fc_remote_port_chkready → drop           | return rc | YES | YES at out | ✅ | |
| fc_block_rport fails → drop              | return rc | YES | YES at out | ✅ | |
| UPLOADING_CONNECTION wait → drop         | return rc | YES | YES at out | ✅ | |
| link not ready → drop                    | return rc | YES | YES at out | ✅ | |
| stop_io_on_error → drop                  | return rc | YES | YES at out | ✅ | |
| **qedf_initiate_abts fails → qedf_scsi_done → drop** | return rc | YES | **EXCESS** (qedf_scsi_done already puts the ref, then out put again) | ❌ | **double put** |
| qedf_initiate_abts success → fallthrough to drop → out | return rc | YES | YES at out | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

When `qedf_initiate_abts` fails, the code calls `qedf_scsi_done()` which (per contract) performs `kref_put` on the io_req refcount, yet afterwards the `out:` label unconditionally puts the same reference again (`if (got_ref) kref_put(...)`), leading to refcount underflow.
```
