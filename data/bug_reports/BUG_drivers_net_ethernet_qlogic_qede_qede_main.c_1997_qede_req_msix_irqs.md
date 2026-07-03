# REAL BUG: drivers/net/ethernet/qlogic/qede/qede_main.c:1997 qede_req_msix_irqs()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

4. **goto out between GET and PUT?** — Not a goto, but the failure path does not call PUT before continuing.

## Full Response

```
## Path Table

| Line    | Return Type            | GET Done? (irq_cpu_rmap_add) | PUT Done? (release) | Balanced? | Notes |
|---------|------------------------|------------------------------|---------------------|-----------|-------|
| L1960   | error return -EINVAL   | NO (no rmap operations)      | N/A                 | ✅        | Before any rmap interaction. |
| L1988   | error return (request_irq failure) | YES (if any irq_cpu_rmap_add called before, including failed ones) | YES (free_irq_cpu_rmap at L1983) | ⚠️ Potentially balanced, but free_irq_cpu_rmap might not completely fix refs from failed adds if notifiers were not attached. Warning targets L1997, not this path. |
| L1997   | success return 0       | YES (any irq_cpu_rmap_add call in the loop, **including failed adds**) | NO (no free_irq_cpu_rmap on success path) | ❌ LEAK   | Unconditional get from irq_cpu_rmap_add happens even on failure (contract). The error path at L1970-1973 does **not** release the reference, and if later iterations succeed, function returns 0 with a dangling refcount. |

**Key detail**: The contract for `irq_cpu_rmap_add` states it is **UNCONDITIONAL** — it always calls `cpu_rmap_get` (increments the rmap refcount) regardless of success or error. When the function fails (`rc != 0`) at L1970, the code merely calls `qede_free_arfs` and *continues* to `request_irq`. There is no `cpu_rmap_put` or `free_irq_cpu_rmap` to release the acquired reference. If the loop completes successfully after such a failure, the function returns 0 at L1997, leaving the rmap with a leaked refcount.

**Pre‑Verdict Checklist**:
1. **"Held for device lifetime"?** — Applies only to the SUCCESS return; the error path (here the failed `irq_cpu_rmap_add` case) is not covered and must release.  
2. **"Ownership transferred"?** — No; the rmap pointer is not transferred, and no cleanup code will release the extra ref from a failed add.  
3. **Unconditional GET?** — Yes, contract says unconditional → GET=YES on every call, even on error.  
4. **goto out between GET and PUT?** — Not a goto, but the failure path does not call PUT before continuing.

## VERDICT: REAL_BUG  
## CONFIDENCE: HIGH  
`irq_cpu_rmap_add` unconditionally increments the rmap refcount. Its failure path inside the loop (L1970‑1973) does not call `free_irq_cpu_rmap` or `cpu_rmap_put`, and the function may later return success at L1997, leaking a reference.
```
