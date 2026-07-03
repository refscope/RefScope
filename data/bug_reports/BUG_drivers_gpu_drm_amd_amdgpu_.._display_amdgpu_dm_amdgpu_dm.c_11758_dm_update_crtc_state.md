# REAL BUG: drivers/gpu/drm/amd/amdgpu/../display/amdgpu_dm/amdgpu_dm.c:11758 dm_update_crtc_state()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L11717 (return 0) | early return after skip_modeset | YES | YES (skip_modeset release) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L11529 (goto fail) | error before new_stream creation | NO (new_stream=NULL) | N/A | ✅ | no stream allocated |
| L11554 (goto fail) | new_stream==NULL | NO | N/A | ✅ | creation failed |
| L11569 (goto fail) | error after creation, new_stream ref=1 | YES (create_validate_stream_for_sink) | YES (fail: dc_stream_release once) | ✅ | |
| L11646 (goto fail) | disable path, new_stream=NULL | NO | N/A | ✅ | |
| L11657 (goto fail) | disable path, new_stream=NULL | NO | N/A | ✅ | |
| L11686 (goto fail) | add‑stream path before skip_modeset, new_stream retained (ref=2) | YES (create + retain) | YES (fail: release once → ref=1 held by crtc state) | ✅ | |
| L11700 (goto fail) | add‑stream path, dc_state_add_stream failed | same as above | YES | ✅ | |
| **L11746 (goto fail)** | **after skip_modeset, color management error** | YES (create) but already put at L11710 | **YES (fail: second release → excess put)** | ❌ **EXCESS PUT** | new_stream not NULLed after skip_modeset; double release |
| L11753 (return ret) | success after skip_modeset | YES | YES (skip_modeset release) | ✅ | |
| L11717 (return 0) | early return after skip_modeset | YES | YES (skip_modeset release) | ✅ | |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

After `skip_modeset` releases `new_stream` via `dc_stream_release(new_stream)` at L11710, the pointer is not cleared. If a later goto fail (e.g., color management error at L11746) is taken, the fail label’s `if (new_stream) dc_stream_release(new_stream)` (L11757) executes a second release, triggering an excess put.
```
