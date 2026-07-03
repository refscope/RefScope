# REAL BUG: drivers/nvme/target/loop.c:347 nvme_loop_init_io_queues()

**Confidence**: MEDIUM | **Counter**: `$->ref.refs.counter`

## Reasoning

4. **goto out between GET and PUT?** – Yes, after `nvmet_cq_init` and `nvmet_sq_init` on previous iterations, the error path goes to `out_destroy_queues`. If that label’s callee doesn’t put the cq, it’s a leak. The warning suggests exactly that.

## Full Response

```
[NEED_SOURCE] nvme_loop_destroy_io_queues

**Path Table for `nvme_loop_init_io_queues()`** (line numbers approximate based on code block)

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L323 | `return ret` (before queues) | NO (no cq initialised) | N/A | ✅ | Early out, no refs held |
| L345 | `return 0` (success) | YES (each i: `nvmet_cq_init` → ref=1, `nvmet_sq_init` success → additional get) | NO (intentionally held for controller lifetime) | ✅ (held-for-lifetime) | Released later by `nvme_loop_destroy_io_queues()` on teardown |
| L338‑343 | `goto out_destroy_queues` (error in iteration `i = k`) | **Current queue** (`i=k`): YES (`nvmet_cq_init`) | **Current queue**: YES (explicit `nvmet_cq_put` on L339) | ✅ for `i=k` | Explicit put releases the initial cq ref from `nvmet_cq_init` |
|   |   | **Previous queues** (`i=1..k-1`): YES (cq_init + sq_init success → refs held) | **Previous queues**: DEPENDS on `nvme_loop_destroy_io_queues()` | ❓ UNKNOWN — if destroy does NOT put those cq refs, LEAK | The warning points to L347, likely inside that destroy function, suggesting missing puts |

`out_destroy_queues` is reached after error. It calls `nvme_loop_destroy_io_queues(ctrl)`, which should release all resources for the queues that were fully initialised (`i<k`). Without its source we cannot confirm – but the smatch warning at line 347 strongly indicates it does **not** release the `nvmet_cq` initial reference for those earlier queues, causing a refcount leak.

**Pre-Verdict Checklist:**
1. **"Held for device lifetime"?** – Only applies to the success return (L345); the error path (L338‑343) must release everything for previous queues.  
2. **"Ownership transferred"?** – No documented transfer or deferred cleanup is visible; the destroy function is expected to do immediate cleanup.  
3. **Unconditional GET?** – `nvmet_cq_init` is unconditional; its ref **must** be paired with a `nvmet_cq_put`.  
4. **goto out between GET and PUT?** – Yes, after `nvmet_cq_init` and `nvmet_sq_init` on previous iterations, the error path goes to `out_destroy_queues`. If that label’s callee doesn’t put the cq, it’s a leak. The warning suggests exactly that.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`nvme_loop_destroy_io_queues` likely fails to release the initial `nvmet_cq` references for queues already initialised (i<k) when an I/O queue init fails, leading to a refcount leak on `nvme_cq`. (Callee source not provided; confidence medium, but smatch warning line 347 supports missing puts.)
```
