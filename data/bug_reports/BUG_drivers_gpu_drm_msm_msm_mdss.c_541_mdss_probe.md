# REAL BUG: drivers/gpu/drm/msm/msm_mdss.c:541 mdss_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L534 | success | YES | NO (immediate put not required) | ✅ | Owned for device lifetime; remove() will of_platform_depopulate |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L522 | error (IS_ERR) | NO (before get) | N/A | ✅ | |
| L532 | error (ret != 0) | YES (of_platform_populate may inc refs) | NO (msm_mdss_destroy doesn't of_platform_depopulate) | ❌ LEAK | Children created before failure not cleaned up; refcount leak on device kref |
| L534 | success | YES | NO (immediate put not required) | ✅ | Owned for device lifetime; remove() will of_platform_depopulate |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_platform_populate` on error path (L532) does not call `of_platform_depopulate`, leaking child device references taken during partial population.
```
