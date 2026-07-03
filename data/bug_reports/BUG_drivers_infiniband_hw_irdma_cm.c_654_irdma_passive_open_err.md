# REAL BUG: drivers/infiniband/hw/irdma/cm.c:654 irdma_passive_open_err()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| after L652   | implicit (reset=0)   | NO        | **YES (irdma_cleanup_retrans_entry + irdma_rem_ref_cm_node)** | ❌        | two puts for one conceptual reference → excess put at L652 |

## Full Response

```
```
| Line         | Return Type          | GET Done? | PUT Done?                                          | Balanced? | Notes |
|--------------|----------------------|-----------|----------------------------------------------------|-----------|-------|
| after L650   | implicit (reset=1)   | YES (irdma_send_reset, unconditional get)          | YES (irdma_cleanup_retrans_entry, unconditional put) | ✅        | net change 0; reference is retained |
| after L652   | implicit (reset=0)   | NO        | **YES (irdma_cleanup_retrans_entry + irdma_rem_ref_cm_node)** | ❌        | two puts for one conceptual reference → excess put at L652 |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
In the `reset=false` path, `irdma_cleanup_retrans_entry` already drops a reference; the subsequent `irdma_rem_ref_cm_node` causes a double-put and an excess-refcount error.
```
