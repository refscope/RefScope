# REAL BUG: drivers/clk/mvebu/ap-cpu-clk.c:342 ap_cpu_clock_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

| 342  | error (ret!=0)   | YES | NO | ❌ LEAK | No `of_node_put(np)` on failure path |

## Full Response

```
| Line | Return Type | GET Done? (of_clk_add_hw_provider on np) | PUT Done? (of_node_put on np) | Balanced? | Notes |
|------|-------------|------------------------------------------|-------------------------------|-----------|-------|
| 243  | error (PTR_ERR) | NO (call not reached) | N/A | ✅ | |
| 262  | error (-EINVAL) | NO | N/A | ✅ | |
| 279  | error (-ENOMEM) | NO | N/A | ✅ | |
| 285  | error (-ENOMEM) | NO | N/A | ✅ | |
| 297  | error (-EINVAL) | NO | N/A | ✅ | |
| 311  | error (-EINVAL) | NO | N/A | ✅ | |
| 331  | error (ret)      | NO | N/A | ✅ | |
| 342  | success (ret==0) | YES | NO (ownership transferred to provider) | ✅ | Provider holds reference |
| 342  | error (ret!=0)   | YES | NO | ❌ LEAK | No `of_node_put(np)` on failure path |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_clk_add_hw_provider(np, ...)` unconditionally increments the reference count on `np`; its error path (non-zero `ret`) returns immediately without `of_node_put(np)`, leaking the reference.
```
