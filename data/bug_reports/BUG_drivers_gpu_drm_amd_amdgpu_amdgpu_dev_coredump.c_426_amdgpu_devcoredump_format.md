# REAL BUG: drivers/gpu/drm/amd/amdgpu/amdgpu_dev_coredump.c:426 amdgpu_devcoredump_format()

**Confidence**: LOW | **Counter**: `$->tbo.base.refcount.refcount.refs.counter`

## Reasoning

normal (end) | UNCLEAR – vm non‑NULL; contract says `→amdgpu_bo_ref(get)` **conditional_on_path** | YES (line 426) | ❓ (excess put if GET not done) | If the function returns a valid `vm` but did **not** increment `root`’s refcount, then the subsequent `amdgpu_bo_unref(&root)` is an excess put |

## Full Response

```
[NEED_SOURCE] amdgpu_vm_lock_by_pasid

## Path Table for `amdgpu_devcoredump_format()` (focus on root refcount balance)

| Path | Line | Return Type | GET Done? (by `amdgpu_vm_lock_by_pasid` on `root`) | PUT Done? (line 426) | Balanced? | Notes |
|------|------|-------------|----------------------------------------------------|----------------------|-----------|-------|
| A | N/A | normal (end) | NO (num_ibs == 0) | NO | ✅ | IB section not entered |
| B | N/A | normal (end) | NO (sizing_pass ⇒ vm = NULL) | NO | ✅ | vm is NULL, no put |
| C | N/A | normal (end) | NO (vm = NULL, lock_by_pasid returned NULL) | NO | ✅ | vm NULL, no put |
| D | N/A | normal (end) | UNCLEAR – vm non‑NULL; contract says `→amdgpu_bo_ref(get)` **conditional_on_path** | YES (line 426) | ❓ (excess put if GET not done) | If the function returns a valid `vm` but did **not** increment `root`’s refcount, then the subsequent `amdgpu_bo_unref(&root)` is an excess put |

## VERDICT: REAL_BUG
## CONFIDENCE: LOW

The warning points to an excess put of the `root` buffer object. The caller unconditionally calls `amdgpu_bo_unref(&root)` when `vm` is non‑NULL, but the contract for `amdgpu_vm_lock_by_pasid` indicates that the get (`amdgpu_bo_ref`) is **conditional_on_path** — i.e., the function may return a valid `vm` without having acquired a reference on `root`. This leads to an extra put on the `root` refcount. Full source of the callee is needed to confirm the exact conditions under which the get is skipped.
```
