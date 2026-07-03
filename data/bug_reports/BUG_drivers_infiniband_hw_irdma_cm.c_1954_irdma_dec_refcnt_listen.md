# REAL BUG: drivers/infiniband/hw/irdma/cm.c:1954 irdma_dec_refcnt_listen()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

loop executes before the `refcount_dec_and_test` check. The warning at line 1954 (the `-EINVAL` return) is one such leaking path.

## Full Response

```
| Line | Return Type | GET Done? (cm_node ref) | PUT Done? | Balanced? | Notes |
|------|-------------|--------------------------|-----------|-----------|-------|
| ~1952 (return 0) | success | YES (if reset_list nodes hit leak condition) | NO (for those nodes) | ❌ LEAK | `irdma_send_reset` error path and `old_state == MPAREQ_RCVD` skip `irdma_rem_ref_cm_node` |
| ~1954 (return -EINVAL) | error | YES (same as above) | NO (for those nodes) | ❌ LEAK | same loop issue, references from `irdma_reset_list_prep` never dropped before return |

The loop iterates over `cm_node` entries placed on `reset_list` by `irdma_reset_list_prep`. That function is expected to take a reference on each node (common pattern for local list processing). The loop must release every reference via `irdma_rem_ref_cm_node`. Two paths fail to do so:
- `irdma_send_reset` fails → no `irdma_rem_ref_cm_node` call.
- `irdma_send_reset` succeeds but `old_state == IRDMA_CM_STATE_MPAREQ_RCVD` → `irdma_rem_ref_cm_node` is skipped.

Both return points can reach these leak scenarios because the loop executes before the `refcount_dec_and_test` check. The warning at line 1954 (the `-EINVAL` return) is one such leaking path.

[NEED_SOURCE] `irdma_reset_list_prep` (to confirm refcount_inc), but the presence of `irdma_rem_ref_cm_node` calls in the loop strongly implies a reference was taken.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Missing `irdma_rem_ref_cm_node()` on send-reset failure and on MPAREQ_RCVD state leaks cm_node references taken by `irdma_reset_list_prep()`.
```
