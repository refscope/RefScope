# REAL BUG: drivers/gpu/drm/i915/gem/i915_gem_dmabuf.c:320 igt_dmabuf_import_same_driver()

**Confidence**: HIGH | **Counter**: `$->base.refcount.refcount.refs.counter`

## Reasoning

- `goto out_import` between GET and PUT? Yes (L262), and the target label `out_import:` only does `i915_gem_object_put(import_obj)`; the code then **falls through** to `out:` which calls `i915_gem_object_put(obj)` again, causing a double put when `import_obj == obj`.

## Full Response

```
```
| Line | Return Type | GET obj? | GET import_obj? | PUT obj? | PUT import_obj? | Balanced? | Notes |
|------|-------------|----------|-----------------|----------|-----------------|-----------|-------|
| L239 (`goto out_ret`) | `__i915_gem_object_create_user` fails | NO (error) | NO | NO | NO | ✅ | No object created |
| L247 (`goto out`) | `i915_gem_prime_export` fails | YES (obj created) | NO | YES (at `out:` L317) | NO | ✅ | |
| L255 (`goto out_dmabuf`) | `i915_gem_prime_import` fails | YES | NO | YES (at `out:` L317) | NO | ✅ | dmabuf_put at `out_dmabuf` releases its reference to obj |
| L262 (`goto out_import`, `import == &obj->base`) | Reuse same object error | YES | NO (import returns same obj, no new ref expected) | YES **twice** (at `out_import:` L313 as `import_obj` put, then fallthrough to `out:` L317) | YES (at `out_import:` L313, same as obj) | ❌ **EXCESS PUT** | Double put on obj → second `i915_gem_object_put(obj)` at L317 operates on refcount already 0 or freed object |
| L270 (`goto out_import`) | `get_pages` fails after lock | YES | YES | YES (at `out:` L317) | YES (at `out_import:` L313) | ✅ | |
| L287 (`goto out_import`) | `verify_access` fails | YES | YES | YES (at `out:` L317) | YES (at `out_import:` L313) | ✅ | |
| L293 (`goto out_import`) | `dma_buf_attach` fails | YES | YES | YES (at `out:` L317) | YES (at `out_import:` L313) | ✅ | |
| L299 (`goto out_detach` → fallthrough) | `dma_buf_map_attachment_unlocked` fails | YES | YES | YES (at `out:` L317) | YES (at `out_import:` L313) | ✅ | |
| success / timeout (fallthrough) | All OK | YES | YES | YES (at `out:` L317) | YES (at `out_import:` L313) | ✅ | |

**Pre-Verdict Checklist:**  
- "Held for device lifetime"? Does not apply; this is a test function.  
- "Ownership transferred"? No; the import object is not transferred to any long-lived structure; both objects are released locally.  
- Unconditional GET? `__i915_gem_object_create_user` and `i915_gem_prime_import` are unconditional on success → GET=YES on all success paths.  
- `goto out_import` between GET and PUT? Yes (L262), and the target label `out_import:` only does `i915_gem_object_put(import_obj)`; the code then **falls through** to `out:` which calls `i915_gem_object_put(obj)` again, causing a double put when `import_obj == obj`.  

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
On the reuse‑error path, `i915_gem_object_put(import_obj)` at `out_import:` (which is the same as `obj`) is followed by a fall‑through to `out:` which calls `i915_gem_object_put(obj)` again → double put, triggering the excess‑put warning.  
```
```
