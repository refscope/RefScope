# REAL BUG: drivers/infiniband/hw/irdma/cm.c:634 irdma_active_open_err()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L634 → end (reset == false) | void return | NO  | YES | NO (excess put) | PUT without any GET inside the function → if caller held only 1 reference, the free after PUT would be followed by use of freed cm_node at L632, L636, L637 |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L634 → end (reset == true)  | void return | YES: refcount_inc(L630) + irdma_send_reset(L631) | YES: irdma_cleanup_retrans_entry(L634) | YES (net +1) but **PUT before GET**; if initial refcount is 1, PUT could free cm_node, then use-after-free at L632 (stats_connect_errs++) and subsequent accesses |
| L634 → end (reset == false) | void return | NO  | YES | NO (excess put) | PUT without any GET inside the function → if caller held only 1 reference, the free after PUT would be followed by use of freed cm_node at L632, L636, L637 |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Unconditional `irdma_cleanup_retrans_entry()` at L634 decrements the refcount before the function finishes using `cm_node`. If the refcount reaches zero, the node is freed, leading to use-after-free on both paths (e.g., `cm_node->cm_core->stats_connect_errs++`). The ordering makes any further access dangerous.
```
