# REAL BUG: drivers/scsi/libfc/fc_disc.c:676 fc_disc_single()

**Confidence**: HIGH | **Counter**: `rdata->kref.refcount.refs.counter`

## Reasoning

L676 (`return fc_disc_gpn_id_req(...)`) | int (success/error) | YES (rdata from fc_rport_create, ref held) | NO (no kref_put anywhere) | ❌ LEAK | Initial refcount from fc_rport_create never released. `fc_disc_gpn_id_req` is unconditional get (adds its own ref), but does not consume caller's ref. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L672 (implicit return, `!rdata`) | error (ENOMEM) | NO (allocation failed) | N/A | ✅ | No reference held. |
| L676 (`return fc_disc_gpn_id_req(...)`) | int (success/error) | YES (rdata from fc_rport_create, ref held) | NO (no kref_put anywhere) | ❌ LEAK | Initial refcount from fc_rport_create never released. `fc_disc_gpn_id_req` is unconditional get (adds its own ref), but does not consume caller's ref. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`fc_rport_create` returns `rdata` with a reference held; after calling `fc_disc_gpn_id_req`, the function returns without ever calling `kref_put` on `rdata`, leaking the reference.
```
