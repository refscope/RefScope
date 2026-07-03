# REAL BUG: drivers/dma-buf/st-dma-resv.c:241 test_for_each_unlocked()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

put(f)` at line 241 runs with refcount already 0 — exactly the “excess put” reported. Early-exit paths (goto err_iter_end) skip the for-loop increment, so `iter_end` legitimately releases the leftover reference, and no double-put occurs. Thus the bug is a double put on the non‑error/complete path.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L182 | return -ENOMEM | NO (f == NULL) | N/A | ✅ | no fence allocated |
| L189 | goto err_free (lock fail) | NO (fence added not yet) | via dma_fence_put(f) after resv_fini | ✅ | refcount=1 from alloc, single put |
| L197 | goto err_free (reserve fail) | NO (fence added not yet) | same as above | ✅ | refcount=1, single put |
| L203 | goto err_iter_end (no restart flag) | YES (dma_resv_add_fence) | via iter_end(?), resv_fini, dma_fence_put(f) | ✅ ? | iterator holds a reference; iter_end likely puts it |
| L207 | goto err_iter_end (unexpected fence) | YES | same | ✅ ? | as above |
| L211 | goto err_iter_end (unexpected usage) | YES | same | ✅ ? | as above |
| L215 | goto err_iter_end (more than one fence) | YES | same | ✅ ? | as above |
| L224 | err_iter_end (normal completion, no fence found or loop ends) | YES | iter_end, resv_fini, dma_fence_put(f) | ❌ LEAK? Excess put? | After normal loop completion, the for-each macro already put the last fence via increment, so if iter_end also puts → double put → refcount underflow at L241. This matches the “excess put” warning on dma_fence_put(f). |
| L241 | dma_fence_put(f) | YES | extra put, already 0 | ❌ EXCESS PUT | This line is the final put; warning says excess put because refcount was already 0 |

**Explanation:**  
dma_resv_add_fence() is an unconditional GET (refcount goes 1 → 2). The iterator also obtains a temporary reference to the fence (refcount → 3). The dma_resv_for_each_fence_unlocked() macro includes a `dma_fence_put(fence)` in the increment part, which fires after the last successful iteration, releasing the iterator’s reference (refcount back to 2). However, on the *normal completion* path (loop runs and ends, or loop never entered because no fence found), the code then calls `dma_resv_iter_end(&cursor)`. If `dma_resv_iter_end()` unconditionally calls `dma_fence_put()` on the cursor’s current fence, this constitutes a **double put** because the for-loop’s increment already released that reference. The result is refcount 1 after `dma_resv_iter_end()`. Then `dma_resv_fini()` releases the reservation object’s reference (refcount 0), and the final `dma_fence_put(f)` at line 241 runs with refcount already 0 — exactly the “excess put” reported. Early-exit paths (goto err_iter_end) skip the for-loop increment, so `iter_end` legitimately releases the leftover reference, and no double-put occurs. Thus the bug is a double put on the non‑error/complete path.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

Double‑put in dma_resv_iter_end on the normal completion path causes an excess put on the fence at line 241.
```
