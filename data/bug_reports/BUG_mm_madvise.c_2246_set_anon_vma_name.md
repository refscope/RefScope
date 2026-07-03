# REAL BUG: mm/madvise.c:2246 set_anon_vma_name()

**Confidence**: LOW | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

formed—likely due to a put after ownership has been transferred (e.g., after storing `anon_name` in a VMA) or a double‑put on an error path. Without the complete source (lines 2234–2246), I cannot fully enumerate all return paths and their GET/PUT status.

## Full Response

```
## Path Table

| Line  | Return Type | GET Done?             | PUT Done? | Balanced? | Notes |
|-------|-------------|-----------------------|-----------|-----------|-------|
| L2223 | error       | NO (before alloc)     | N/A       | ✅ | strndup_user returned error, no anon_name alloc. |
| L2231 | error       | NO (before alloc)     | N/A       | ✅ | Invalid name character, kfree(name), no alloc. |
| L2237 | error       | NO (alloc returned NULL) | N/A    | ✅ | Alloc failed, anon_name is NULL, no ref taken. |
| L2246 | *** missing source *** | Likely YES (non-NULL anon_name from successful alloc) | YES? Excess put | ❌ EXCESS PUT | Warning at this line: refcount excess put. The rest of `set_anon_vma_name()` is not provided; need full source to identify exact branch. |

**Note:** The function `set_anon_vma_name()` continues after the provided snippet. The warning line 2246 is after the `!anon_name` check (L2237), meaning `anon_name` is non‑NULL and holds a kref reference (1 from kref_init in `anon_vma_name_alloc`). The “excess put” implies that the reference count drops to zero too early or an extra put is performed—likely due to a put after ownership has been transferred (e.g., after storing `anon_name` in a VMA) or a double‑put on an error path. Without the complete source (lines 2234–2246), I cannot fully enumerate all return paths and their GET/PUT status.

---

[NEED_SOURCE] set_anon_vma_name

---

VERDICT: REAL_BUG  
CONFIDENCE: LOW  
Excess put at L2246 strongly suggests a double‑put or early put after successful `anon_vma_name_alloc()`. Need full function body to confirm the exact path and ownership transfer.
```
