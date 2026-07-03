# REAL BUG: drivers/gpu/drm/amd/amdgpu/../display/dc/core/dc.c:5370 update_planes_and_stream_v2()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| ~5370 | success, dc->current_state == context, minimal transition entered and succeeded | YES (GET1 + GET2) | NO (no release) | ❌ LEAK | both references leaked |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~5302 | error (commit_minimal_transition_state on current_state fails) | NO (context not acquired) | N/A | ✅ | context unaffected |
| ~5310 | error (update_planes_and_stream_state fails) | NO (context not assigned) | N/A | ✅ | |
| ~5317 | error (commit_minimal_transition_state on context fails) | YES (GET1 from update_planes_and_stream_state) | YES (dc_state_release called) | ✅ | explicit release |
| ~5370 | success, dc->current_state != context, minimal transition not entered | YES (GET1) | NO (ownership transferred via swap; no put needed) | ✅ | context reference given to dc |
| ~5370 | success, dc->current_state != context, minimal transition entered and succeeded | YES (GET1 + GET2) | NO (swap transfers only one ref; extra GET2 leaked) | ❌ LEAK | extra get from commit_minimal_transition_state not released |
| ~5370 | success, dc->current_state == context, minimal transition not entered | YES (GET1) | NO (no swap, no release) | ❌ LEAK | leak of the reference from update_planes_and_stream_state |
| ~5370 | success, dc->current_state == context, minimal transition entered and succeeded | YES (GET1 + GET2) | NO (no release) | ❌ LEAK | both references leaked |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`commit_minimal_transition_state(dc, context)` succeeds → acquires extra reference; on exit path when `dc->current_state != context`, swap only transfers one reference, leaking the extra; when `dc->current_state == context`, no release at all, leaking any acquired references.
```
