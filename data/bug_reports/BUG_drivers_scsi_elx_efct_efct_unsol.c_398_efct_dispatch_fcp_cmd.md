# REAL BUG: drivers/scsi/elx/efct/efct_unsol.c:398 efct_dispatch_fcp_cmd()

**Confidence**: LOW | **Counter**: `io->ref.refcount.refs.counter`

## Reasoning

at line 398 (the `efct_scsi_recv_cmd` call site) points to an internal double-put or incorrect reference drop within `efct_scsi_recv_cmd`, not in the enclosing function. Without the source of `efct_scsi_recv_cmd`, the cause of the excess-put cannot be determined.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L343 | error       | NO (before get) | N/A  | ✅ | seq payload NULL, no io allocated |
| L347 | error       | NO (before get) | N/A  | ✅ | validate fails, no io allocated |
| L350 | error       | NO (before get) | N/A  | ✅ | bad LUN, no io allocated |
| L356 | error       | NO (get failed) | N/A  | ✅ | efct_scsi_io_alloc returned NULL |
| **L367** | **error** | **YES** (unconditional GET at L351 succeeded) | **NO** | **❌ LEAK** | FCP_CFL_LEN_MASK check fails, return -EIO without putting io |
| L371a| success, tm_flags branch | YES | **NO** (dispatch_unsol_tmf likely no put) | **❌ LEAK** (if tmf doesn't take ownership) | Missing put; ownership transfer unverified |
| L371b| success, recv_cmd branch | YES | **Conditional** (recv_cmd may put on error) | **⚠️ depends on recv_cmd** | recv_cmd may free on error, else takes ownership (transfer); excess put warning may originate inside recv_cmd |

**Warning origin**: The “refcount excess put” warning at line 398 (the `efct_scsi_recv_cmd` call site) points to an internal double-put or incorrect reference drop within `efct_scsi_recv_cmd`, not in the enclosing function. Without the source of `efct_scsi_recv_cmd`, the cause of the excess-put cannot be determined.

[NEED_SOURCE] efct_scsi_recv_cmd

VERDICT: UNCLEAR
CONFIDENCE: LOW
The excess-put warning is inside `efct_scsi_recv_cmd`, whose internal implementation is missing. Local analysis reveals a definite refcount leak on the FCP_CFL_LEN_MASK error path (L367), but that is a separate leak, not an excess put. The actual warning requires `efct_scsi_recv_cmd` source to assess double-put scenarios.
```
