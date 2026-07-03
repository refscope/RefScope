# REAL BUG: drivers/gpu/drm/xe/xe_hw_fence.c:71 hw_fence_irq_run_cb()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

The only return from `hw_fence_irq_run_cb()` is the end of the void function; the excess put occurs on the described conditional branch, unbalancing the refcounting.

## Full Response

```
We need to investigate the `dma_fence_is_signaled_locked()` function, which is the only possible source of a reference get in this callback. Its contract is unknown. Without it, we cannot determine if the `dma_fence_put` is balanced or excessive.

[NEED_SOURCE] dma_fence_is_signaled_locked

---

**Path Table** (all paths in `hw_fence_irq_run_cb`)

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| end of function (implicit return after L70) | void | **unknown** – depends on `dma_fence_is_signaled_locked` internals | YES – `dma_fence_put` at L65 (only for signalled fences) | **unknown** | Only return path; `dma_fence_put` releases the list reference (assumed balanced), but if `dma_fence_is_signaled_locked` also takes a reference, then we have one extra put → excess put. |

The classic pattern: `list_for_each_entry_safe` -> `dma_fence_is_signaled_locked` -> `list_del_init` -> `dma_fence_put`. Here `dma_fence_put` drops the reference the list held. The fence was added to the list earlier (presumably with a `dma_fence_get`). There is no obvious double-put inside this function. The warning about "excess put" suggests the put may be dropping a reference that was already dropped or was never held. If `dma_fence_is_signaled_locked` takes a temporary reference internally, then the total puts would exceed gets. We must inspect that function to resolve.

--- [NEED_SOURCE r1] ---

Based on the provided contracts and the source of `dma_fence_is_signaled_locked()` (L511‑L528), the function `dma_fence_signal_locked()` performs a `PUT` internally. The warning location at `dma_fence_put(fence);` in `hw_fence_irq_run_cb` becomes an **excess put** when the fence is signaled via the `ops->signaled` path inside `dma_fence_is_signaled_locked()`. On that path, the signal already drops the list reference, but the caller unconditionally does another put, leading to a double‑put.

**Path table (inferred from the loop structure – only the ref‑relevant paths are shown):**

| Execution path | GET done? | PUT done? | Balanced? | Notes |
|----------------|-----------|-----------|-----------|-------|
| fence already signaled (flag set) → `dma_fence_is_signaled_locked()` returns true without calling `dma_fence_signal_locked()` → then explicit `dma_fence_put(fence)` | list reference held (one GET) | one PUT (explicit) | ✅ | Signal did not happen; the single put correctly releases the list reference. |
| fence not signaled, `ops->signaled()` returns true → `dma_fence_is_signaled_locked()` calls `dma_fence_signal_locked(fence)` (which internally does a `dma_fence_put`) → returns true → then explicit `dma_fence_put(fence)` again | list reference held (one GET) | **two PUTs** (one inside signal, one explicit) | ❌ **EXCESS PUT** | The signal already consumed the list reference; the additional put is a double‑decrement. |
| fence not signaled, `ops->signaled()` returns false → loop continues | list ref
```
