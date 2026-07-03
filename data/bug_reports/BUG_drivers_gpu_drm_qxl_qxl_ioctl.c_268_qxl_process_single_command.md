# REAL BUG: drivers/gpu/drm/qxl/qxl_ioctl.c:268 qxl_process_single_command()

**Confidence**: HIGH | **Counter**: `$->release_count.counter`

## Reasoning

| success     | YES (alloc succeeded)    | NO (ownership transferred to ring)     | (depends) | Balanced if ring takes ownership; smatch may flag as leak. The main inconsistency is the double‑free above.                                                                                      |

## Full Response

```
| Line(s)                                     | Return Type | GET Done?                | PUT Done?                              | Balanced? | Notes                                                                                                                                                                                             |
|----------------------------------------------|-------------|--------------------------|----------------------------------------|-----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 152,155,159,163 (early returns)              | error       | NO (before alloc)        | N/A                                    | ✅        |                                                                                                                                                                                                   |
| 167 (goto out_free_reloc after alloc fails)  | error       | NO (get failed)          | N/A                                    | ✅        | `qxl_alloc_release_reserved` failed → no release ref held                                                                                                                              |
| 185 (goto out_free_release for unwritten)    | error       | YES (alloc succeeded)    | YES (`qxl_release_free` via out_free_release) | ✅        | `ret` = -EFAULT, so PUT happens                                                                                                                                                                   |
| Loop: multiple goto out_free_bos (reloc errors) | error       | YES                      | YES (`qxl_release_free` via out_free_bos→out_free_release) | ✅        | All these set `ret` non‑zero, so PUT called                                                                                                                                                       |
| `qxl_release_reserve_list` failure, goto out_free_bos | error       | YES                      | YES (explicit `qxl_release_free`)      | ❌        | **Double‑put**: `qxl_release_reserve_list` already calls `qxl_release_free` on error (internal cleanup), then the caller frees again → refcount underflow. This matches the “inconsistent” warning. |
| Success path (push succeeds, ret=0)          | success     | YES (alloc succeeded)    | NO (ownership transferred to ring)     | (depends) | Balanced if ring takes ownership; smatch may flag as leak. The main inconsistency is the double‑free above.                                                                                      |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
qxl_release_reserve_list failure path already frees the release, then the caller’s `qxl_release_free` causes a double put, making the release_count refcounting inconsistent.
```
