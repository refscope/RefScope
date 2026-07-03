# REAL BUG: drivers/staging/greybus/fw-download.c:464 gb_fw_download_connection_exit()

**Confidence**: HIGH | **Counter**: `fw_req->kref.refcount.refs.counter`

## Reasoning

p body, function returns void) | normal return (implicit after loop) | YES (kref_get at L453 inside first loop) | YES (free_firmware put + explicit put_fw_req) | ❌ | free_firmware already calls put_fw_req; the following put_fw_req causes an **excess put** (double release after a single kref_get) |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L441 | early return | N/A (no fw_req) | N/A | ✅ | connection == NULL, no fw_req operations |
| L464 (loop body, function returns void) | normal return (implicit after loop) | YES (kref_get at L453 inside first loop) | YES (free_firmware put + explicit put_fw_req) | ❌ | free_firmware already calls put_fw_req; the following put_fw_req causes an **excess put** (double release after a single kref_get) |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`free_firmware()` unconditionally calls `put_fw_req()`, then the loop body immediately calls `put_fw_req()` again, resulting in two releases for the single `kref_get` taken in the earlier loop. This is an excess put.
```
