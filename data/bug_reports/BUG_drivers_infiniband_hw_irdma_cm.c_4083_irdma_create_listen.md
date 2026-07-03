# REAL BUG: drivers/infiniband/hw/irdma/cm.c:4083 irdma_create_listen()

**Confidence**: MEDIUM | **Counter**: `$->refcnt.refs.counter`

## Reasoning

3), the extra decrement causes an **excess put / refcount underflow**. This is a real bug rooted in the refcount handling of the node creation, but the warning manifests at this line. The success path does not call `irdma_cm_del_listen`, so no underflow there.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3978 | error (-EINVAL) | NO (before get) | N/A | ✅ | device pointer null, no listener created |
| L3985 | error (-EINVAL) | NO (before get) | N/A | ✅ | IPv4 MTU check failed, before any get |
| L4003 | error (-EINVAL) | NO (before get) | N/A | ✅ | IPv6 MTU check failed, before any get |
| L4021 | error (-ENOMEM) | NO (get returned NULL) | N/A | ✅ | `irdma_make_listen_node` returned NULL, no reference held |
| L4038 (goto error from `irdma_add_mqh`) | error | YES (unconditional get from `irdma_make_listen_node`) | YES (`irdma_cm_del_listen` called) | ❌ EXCESS PUT | Contract shows `irdma_make_listen_node` does `refcount_set`+`refcount_dec`, leaving refcount at 0; subsequent put in `irdma_cm_del_listen` underflows |
| L4045 (goto error from `irdma_manage_qhash`) | error | YES | YES | ❌ EXCESS PUT | same issue |
| L4051 (goto error from `irdma_add_apbvt`) | error | YES | YES | ❌ EXCESS PUT | same issue |
| L4081 | success (return 0) | YES | NO (ownership transferred to `cm_id->provider_data`) | ✅ | reference held by cm_id, no put needed here |

🔴 **Key finding:** The GET contract for `irdma_make_listen_node` states it performs `refcount_set(set),refcount_dec(put)` on the returned node’s `refcnt.refs.counter`. This implies the node’s refcount is **decremented** inside the get function (or left at a net 0 after initial set). When `irdma_create_listen` later calls `irdma_cm_del_listen` on error paths (line 4083), the extra decrement causes an **excess put / refcount underflow**. This is a real bug rooted in the refcount handling of the node creation, but the warning manifests at this line. The success path does not call `irdma_cm_del_listen`, so no underflow there.

[NEED_SOURCE] irdma_make_listen_node

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`irdma_make_listen_node` leaves the node’s refcount at 0 (according to its contract), causing the subsequent put in `irdma_cm_del_listen` on error paths to underflow.
```
