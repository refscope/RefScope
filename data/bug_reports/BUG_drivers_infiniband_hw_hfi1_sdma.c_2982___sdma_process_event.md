# REAL BUG: drivers/infiniband/hw/hfi1/sdma.c:2982 __sdma_process_event()

**Confidence**: HIGH | **Counter**: `sde->state.kref.refcount.refs.counter`

## Reasoning

**Result:** The path `s00_hw_down` → `sdma_event_e40_sw_cleaned` calls `sdma_sw_tear_down()` without ever having called `sdma_get()`. This causes a spurious `kref_put` on a reference that was never taken, leading to the reported “refcount excess put”.

## Full Response

```
```
## Path Table (Event Paths with Refcount Operations in `__sdma_process_event`)

| State / Event                | GET Done? (sdma_get) | PUT Done? (sdma_sw_tear_down) | Balanced? | Notes                                                                     |
|------------------------------|----------------------|-------------------------------|-----------|---------------------------------------------------------------------------|
| s00_hw_down → e10/e30        | YES (explicit get at L2532) | NO (put deferred to later state transition) | PENDING  | Get acquired, state moves to s10; later put will balance when tear_down called in appropriate state |
| s00_hw_down → e40_sw_cleaned | **NO**               | **YES** (direct call at L2540) | ❌ **EXCESS PUT** | No matching `sdma_get` executed before this event; refcount was never incremented, put would over-decrement |
| s10 → e00_go_hw_down         | YES (prior get in s00→s10) | YES               | ✅         | Get was acquired earlier; put releases it                                   |
| s15 → e00_go_hw_down         | YES (prior get)      | YES               | ✅         | Same as above                                                              |
| s20_idle → e00_go_hw_down    | YES (prior get; all paths into s20 come from states that had a get) | YES | ✅     | Balanced                                                                   |
| s30 → e00_go_hw_down         | N/A (no tear_down)   | -                 | -          | No put in this transition                                                  |
| s40 → e00_go_hw_down         | YES (prior get)      | NO (schedules tasklet for sw_clean_up, which later puts) | ⚠️ Deferred  | Put will happen via tasklet; overall lifecycle balanced if no double-put |
| s50 → e00_go_hw_down         | YES (prior get)      | NO (schedules tasklet)         | Deferred   | Same as s40                                                                |
| s60 → e00_go_hw_down         | YES (prior get)      | NO (schedules tasklet)         | Deferred   | Same as s40                                                                |
| s80 → e00_go_hw_down         | YES (prior get)      | NO (schedules tasklet)         | Deferred   | Same as s40                                                                |
| s82 → e00_go_hw_down         | YES (prior get)      | NO (schedules tasklet)         | Deferred   | Same as s40                                                                |
| s99 → e00_go_hw_down         | YES (prior get)      | NO (schedules tasklet)         | Deferred   | Same as s40                                                                |

## Pre-Verdict Checklist

1. **"Held for device lifetime"?** → No such claim. All references are dynamic.
2. **"Ownership transferred"?** → No ownership transfer, just direct get/put pair.
3. **Unconditional GET?** → Yes, `sdma_get` is unconditional. If `sdma_sw_tear_down` is called without a prior get, refcount would go neg
```
