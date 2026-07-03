# REAL BUG: drivers/net/wwan/wwan_core.c:219 wwan_put_debugfs_dir()

**Confidence**: HIGH | **Counter**: `wwandev->dev.kobj.kref.refcount.refs.counter`

## Reasoning

c changes this: the function itself is the sole owner of the reference acquired inside its body. The comment “also got a reference” does not justify a second `put_device`; it likely refers to the caller’s reference, but that should not be released here. The code should call `put_device` only once.

## Full Response

```
## Path Table

| Line (approx) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|---------------|-------------|-----------|-----------|-----------|-------|
| L215 (early return) | void return | NO (IS_ERR guard – `get_by_debugfs` failed, no ref acquired) | NO (no put executed) | ✅ | IS_ERR prevents use of invalid pointer |
| After L219 (normal path) | void return (end of function) | YES (`wwandev` valid, `wwan_dev_get_by_debugfs` acquired a reference on `dev.kobj`) | YES (two `put_device` calls) | ❌ EXCESS PUT | One get, two puts → refcount will underflow |

## Analysis

- **Get contract**: `wwan_dev_get_by_debugfs()` is **conditional** – returns a valid `wwan_device` pointer **with a reference acquired** (via `class_find_device(get)`), or an `ERR_PTR` on failure.  
- **Put contract**: `put_device()` releases one reference.  

In the normal path (no `IS_ERR`), the function calls `put_device(&wwandev->dev)` **twice**, releasing two references when only one was obtained. This is a clear excess put, as the warning “refcount excess put” indicates.

No ownership transfer, deferred release, or devm mechanic changes this: the function itself is the sole owner of the reference acquired inside its body. The comment “also got a reference” does not justify a second `put_device`; it likely refers to the caller’s reference, but that should not be released here. The code should call `put_device` only once.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH
```
