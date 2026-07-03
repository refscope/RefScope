# REAL BUG: drivers/gpu/drm/msm/disp/mdp5/mdp5_crtc.c:1033 mdp5_crtc_cursor_set()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| L984 (!handle) → end | return ret | *UNCERTAIN (get ret unchecked)* | YES (unconditional) | ❌ underflow if get fails | same |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L966 | error       | NO (before get) | N/A  | ✅ | |
| L971 | error       | NO (before get) | N/A  | ✅ | |
| L975 | error       | NO (before get) | N/A  | ✅ | |
| L979 | error       | NO (before get) | N/A  | ✅ | |
| L989 | error (ENOENT) | NO (before get) | N/A  | ✅ | cursor_bo lookup failed |
| L994 | error       | NO (before get) | N/A  | ✅ | iova pin fail before get |
| L999 (handle success) → end | return ret | *UNCERTAIN (get ret unchecked)* | YES (unconditional) | ❌ underflow if get fails | get not checked, put always called |
| L984 (!handle) → end | return ret | *UNCERTAIN (get ret unchecked)* | YES (unconditional) | ❌ underflow if get fails | same |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_get_sync` calls at L984 and L999 have return values ignored; unconditional `pm_runtime_put_sync` at L1022 causes refcount underflow when get fails.
```
