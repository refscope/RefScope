# REAL BUG: drivers/gpu/drm/i915/gvt/scheduler.c:730 intel_vgpu_shadow_mm_pin()

**Confidence**: HIGH | **Counter**: `$->pincount.counter`

## Reasoning

entries: GET=YES → PUT=YES (reverse). For **failed** entry: GET=NO (pin returned error) → PUT=YES (reverse loop starts from failed entry) | ❌ LEAK   | **BUG** – `list_for_each_entry_from_reverse(m, ...)` includes the entry whose `intel_vgpu_pin_mm()` failed. That entry should not be unpinned. |

## Full Response

```
## Path Table

| Line (approx) | Return Type      | Shadow MM GET? | Shadow MM PUT? | LRI MM(s) GET/PUT?                                          | Balanced? | Notes                                                              |
|---------------|------------------|----------------|----------------|-------------------------------------------------------------|-----------|---------------------------------------------------------------------|
| L5            | error (pin fail) | NO (pin failed)| N/A            | N/A                                                         | ✅        | Initial pin of shadow failed, return early; no ref taken.          |
| L11           | error (type fail)| YES            | YES            | N/A                                                         | ✅        | Shadow pinned then explicit unpin; balanced.                        |
| L27 (success) | success (ret=0)  | YES            | NO (kept)      | All LRI entries pinned (GET=YES, PUT=NO)                    | ✅        | Success path; all references held for caller.                       |
| L27 (error)   | error (LRI fail) | YES            | YES (via L26)  | For successfully pinned LRI entries: GET=YES → PUT=YES (reverse). For **failed** entry: GET=NO (pin returned error) → PUT=YES (reverse loop starts from failed entry) | ❌ LEAK   | **BUG** – `list_for_each_entry_from_reverse(m, ...)` includes the entry whose `intel_vgpu_pin_mm()` failed. That entry should not be unpinned. |

## VERDICT: REAL_BUG

CONFIDENCE: HIGH

**Reasoning:** When `intel_vgpu_pin_mm(m)` fails inside the LRI loop, the reverse‑unpin loop starts from the **failed** entry (`m`), which has no valid reference. This causes an extra `intel_vgpu_unpin_mm(m)` call, leading to an inconsistent refcount (over‑decrement) for that LRI mm. The contract (conditional get – failure returns non‑zero and takes no reference) is clear from the code logic. The bug is not a false positive.
```
