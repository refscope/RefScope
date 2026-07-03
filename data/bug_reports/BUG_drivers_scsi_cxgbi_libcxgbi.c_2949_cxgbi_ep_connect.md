# REAL BUG: drivers/scsi/cxgbi/libcxgbi.c:2949 cxgbi_ep_connect()

**Confidence**: HIGH | **Counter**: `$->refcnt.refcount.refs.counter`

## Reasoning

| L: successful alloc & return ep | success | YES (two gets) | NO (no put in this function) | ❌ LEAK | endpoint holds csk; double get never balanced (endpoint will likely put only once) |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L: aft addr_family check (sa_family not AF_INET/AF_INET6) | error | NO (before any get) | N/A | ✅ | returns ERR_PTR(-EAFNOSUPPORT) |
| L: aft IS_ERR(csk) check | error | NO (get follows this guard) | N/A | ✅ | returns ERR_CAST(csk) |
| L: "Could not connect … goto release_conn" (hba mismatch, ifindex match) | error | YES (cxgbi_sock_get) | YES (release_conn put) | ✅ | single get, single put via release_conn |
| L: sock_get_port error → goto release_conn | error | YES (cxgbi_sock_get + sock_get_port → two gets) | YES (one put via release_conn) | ❌ LEAK | two gets, one put; extra ref remains |
| L: csk_init_act_open error → goto release_conn | error | YES (two gets) | YES (one put) | ❌ LEAK | same as above |
| L: cxgbi_sock_is_closing -> goto release_conn | error | YES (two gets) | YES (one put) | ❌ LEAK | same |
| L: iscsi_create_endpoint fails -> goto release_conn | error | YES (two gets) | YES (one put) | ❌ LEAK | same |
| L: successful alloc & return ep | success | YES (two gets) | NO (no put in this function) | ❌ LEAK | endpoint holds csk; double get never balanced (endpoint will likely put only once) |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

`sock_get_port` unconditionally calls `cxgbi_sock_get`, adding a second ref after the explicit `cxgbi_sock_get`. Every error path after that point, plus the success return, only releases a single reference (via `release_conn` or none), leaking at least one reference on all paths.
```
