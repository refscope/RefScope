# REAL BUG: drivers/gpu/drm/amd/amdgpu/../display/dc/core/dc.c:7584 update_planes_and_stream_cleanup_v3()

**Confidence**: HIGH | **Counter**: `scratch->dc->current_state->refcount.refcount.refs.counter`

## Reasoning

| SEAMLESS break, falls through to `return false` | false | NO (intermediate not called) | YES (`swap_and_release_current_context` called) | ✅ | get was not done in this case, swap balances any previous ref |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L7570 (MINIMAL_NEW deferred false, return true) | success (return true) | YES (unconditional get via `update_planes_and_stream_cleanup_v3_intermediate`) | NO (no `swap_and_release_current_context`) | ❌ LEAK | early return skips put on `current_state` |
| L7584 (MINIMAL_CURRENT, return true) | success (return true) | YES (unconditional get via intermediate) | NO | ❌ LEAK | returns without `swap_and_release_current_context` |
| MINIMAL_NEW deferred true, falls through to `return false` | error/false | YES (intermediate called) | NO | ❌ LEAK | `swap_and_release_current_context` not called, only `new_context` released |
| FAST/FULL break, falls through to `return false` | false | NO (intermediate not called) | N/A | ✅ | |
| SEAMLESS break, falls through to `return false` | false | NO (intermediate not called) | YES (`swap_and_release_current_context` called) | ✅ | get was not done in this case, swap balances any previous ref |
| INVALID/default fall through | false | NO | N/A | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`update_planes_and_stream_cleanup_v3_intermediate` unconditionally gets `current_state`, but the `MINIMAL_NEW` (deferred false) and `MINIMAL_CURRENT` paths return true without calling `swap_and_release_current_context`, leaking the reference.
```
