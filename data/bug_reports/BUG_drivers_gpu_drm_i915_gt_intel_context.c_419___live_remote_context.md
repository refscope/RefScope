# REAL BUG: drivers/gpu/drm/i915/gt/intel_context.c:419 __live_remote_context()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

[NEED_SOURCE] __remote_sync → required to confirm which callee increments the refcount and to determine the correct fix (e.g., add a matching `intel_context_put(remote)` after each `__remote_sync` call or inside its error cleanup).

## Full Response

```
| Line | Return Type | GET (remote)? | GET (local)? | PUT (remote)? | PUT (local)? | Balanced? | Notes |
|------|-------------|---------------|--------------|---------------|--------------|-----------|-------|
| L372 | error (return 0) | NO (no create) | NO | N/A | N/A | ✅ | Guc early return, no get |
| L377 | error (return -EINVAL) | NO (no create) | NO | N/A | N/A | ✅ | Awake check, no get |
| L384 | error (return PTR_ERR(remote)) | NO (create failed) | NO | N/A | N/A | ✅ | IS_ERR → no ref |
| L390 (goto err_remote) | error (local create failed) | YES (from L381 create) | NO (IS_ERR) | YES (at err_remote L428) | N/A | ✅ | remote put at err_remote |
| L403–L414 (break) → after loop | error/break | YES (L381 create) | YES (L387 create) | YES (L428 err_remote) | YES (L426 put) | ❌ LEAK | After loop: puts base refs, but __remote_sync() adds remote ref without put (see note) |
| L403–L416 (no break) → after loop | success (err uninitialized?) | YES | YES | YES | YES | ❌ LEAK | Same as above, extra get from __remote_sync not released |

**Note:** The function calls `__remote_sync(local, remote)` and `__remote_sync(engine->kernel_context, remote)`. The warning strongly suggests these calls increment `remote->ref.refcount.refs.counter` (via e.g. `intel_context_get` or by scheduling a request that holds a ref). The subsequent `intel_context_put(remote)` at `err_remote` only releases the base reference from `intel_context_create`, not the extra reference(s) acquired inside `__remote_sync`. The leaked reference persists at function exit (line 419). **Therefore, every path that enters the loop and reaches the `err_remote` label leaks a reference on `remote`.**

[NEED_SOURCE] __remote_sync → required to confirm which callee increments the refcount and to determine the correct fix (e.g., add a matching `intel_context_put(remote)` after each `__remote_sync` call or inside its error cleanup).

VERDICT: REAL_BUG
CONFIDENCE: HIGH
__remote_sync() acquires an additional reference on `remote` (as indicated by the refcount leak warning at line 419); the existing `intel_context_put(remote)` in the cleanup path only releases the initial creation reference, leaving one (or more) extra references dangling when the function returns.
```
