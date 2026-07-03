# REAL BUG: drivers/gpu/drm/amd/amdgpu/../display/amdgpu_dm/amdgpu_dm.c:12217 dm_update_plane_state()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| Out cursor fallback (ret != 0) | return ret | N/A | N/A | ✅ | No imbalance |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L12082 (cursor, ret != 0) | return ret | NO | N/A | ✅ | Before any get/put |
| L12084 (cursor, ret == 0) | return 0 | NO | N/A | ✅ | - |
| L12095 (!needs_reset, disable) | return 0 | NO | N/A | ✅ | - |
| L12098 (!old_plane_crtc) | return 0 | NO | N/A | ✅ | - |
| L12105 (!stream) | return 0 | NO | N/A | ✅ | - |
| L12113 (dm_atomic_get_state error) | return ret | NO | N/A | ✅ | - |
| L12119 (dc_state_remove_plane fail) | return -EINVAL | NO (remove failed) | NO | ✅ | No release on failure path |
| **L12217 (disable branch, after remove success)** | **then → return 0 at end** | **NO (get in earlier call)** | **YES (dc_plane_state_release)** | **❌ EXCESS PUT** | dc_state_remove_plane already dropped stream’s ref; explicit release causes underflow |
| L12161 (add, disabling) | return 0 | NO | N/A | ✅ | - |
| L12164 (!new_plane_crtc) | return 0 | NO | N/A | ✅ | - |
| L12171 (!stream) | return 0 | NO | N/A | ✅ | - |
| L12174 (!needs_reset) | return 0 | NO | N/A | ✅ | - |
| L12179 (check_state fail) | goto out → return ret | NO | N/A | ✅ | - |
| L12185 (dc_create_plane_state fail) | goto out → return ret | NO (alloc failed) | N/A | ✅ | - |
| L12193 (fill_attributes fail) | release → goto out → return ret | YES | YES | ✅ | Proper release on error |
| L12202 (dm_atomic_get_state fail) | release → goto out → return ret | YES | YES | ✅ | - |
| L12212 (add_plane fail) | release → goto out → return ret | YES | YES | ✅ | - |
| After add_plane success | return 0 (end) | YES (create + add_plane get) | NO explicit (owned by stream) | ✅ | Stream will release later |
| Out cursor fallback (ret != 0) | return ret | N/A | N/A | ✅ | No imbalance |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
The explicit `dc_plane_state_release()` at line 12217 after a successful `dc_state_remove_plane()` causes a refcount underflow because `dc_state_remove_plane()` already drops the stream’s reference. The add‑branch comment explicitly states that after `dc_state_add_plane()` the plane is owned by the stream and released when the atomic state is cleaned; the corresponding removal function is expected to handle that release, making the extra put a double‑free.
```
