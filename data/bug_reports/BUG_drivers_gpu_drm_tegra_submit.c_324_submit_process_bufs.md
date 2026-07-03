# REAL BUG: drivers/gpu/drm/tegra/submit.c:324 submit_process_bufs()

**Confidence**: HIGH | **Counter**: `mapping->ref.refcount.refs.counter`

## Reasoning

| Ldone | returns err | various | various | success path unbalanced | done label does not call any put; error paths already balanced before reaching done |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L265 | error (PTR_ERR) | NO (before any GET) | N/A | ✅ | `bufs` allocation failed, no mappings yet |
| L276 | error (goto done) | NO (before loop) | N/A | ✅ | `mappings` kzalloc failed, loop not entered |
| L286 | error (goto drop_refs) | NO for this iteration (flags check before GET); for i>0, previous GETs released by `while(i--) put(...)` | YES (previous mappings put via drop_refs) | ✅ | Flags check before `tegra_drm_mapping_get`; drop_refs handles previous iterations |
| L293 | error (goto drop_refs) | NO for this iteration (GET returned NULL); for i>0, previous GETs released | YES (previous mappings put) | ✅ | `mapping == NULL` → no ref taken; drop_refs handles earlier ones |
| L299 | error (goto drop_refs) | YES (current mapping GET succeeded) | YES (explicit `tegra_drm_mapping_put(mapping)` + drop_refs for earlier) | ✅ | Error path explicitly puts current mapping, drop_refs releases prior ones |
| L306–307 | success (goto done) | YES (all `args->num_bufs` mappings acquired) | NO | ❌ LEAK | Loop completed, references stored in `job_data->used_mappings` but never released here; no evidence of cleanup elsewhere in provided context |
| Ldone | returns err | various | various | success path unbalanced | done label does not call any put; error paths already balanced before reaching done |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
On the success path (`goto done` after loop), every buffer’s `tegra_drm_mapping_get()` returns a non‑NULL mapping with an elevated reference count, but `submit_process_bufs` exits without ever calling `tegra_drm_mapping_put()` on those references. The array is handed to `job_data->used_mappings` but the provided source contains no evidence of a guaranteed release mechanism (no cleanup function visible, no devm registration, no documentation of ownership transfer). According to the strict contract‑driven rules, an unconditional GET without a corresponding PUT on the same path is a refcount leak.
```
