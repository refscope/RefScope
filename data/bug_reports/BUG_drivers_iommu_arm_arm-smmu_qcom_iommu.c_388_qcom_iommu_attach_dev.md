# REAL BUG: drivers/iommu/arm/arm-smmu/qcom_iommu.c:388 qcom_iommu_attach_dev()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

| L386 | error (sanity check) | same as L379 | YES (L377) | ❌ POTENTIAL IMBALANCE | same issue |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L371 | error       | NO (before get) | N/A  | ✅ | get hasn't happened yet |
| L379 | error (ret<0) | ⚠️ get called at L375, return value NOT checked. Contract: increments only on success (≥0), no inc on error (<0). So: <br>• If get succeeded: GET=YES (counter inc)<br>• If get failed: GET=NO (no inc) | YES (pm_runtime_put_sync always called at L377) | ❌ POTENTIAL IMBALANCE: If get failed, put without matching get → refcount underflow. | Unconditional put after unchecked conditional get. |
| L386 | error (sanity check) | same as L379 | YES (L377) | ❌ POTENTIAL IMBALANCE | same issue |
| L388 | success     | same as L379 | YES (L377) | ❌ POTENTIAL IMBALANCE | same issue |

**Apply PRE-VERDICT CHECKLIST:**

1. **“Held for device lifetime”?** — Not applicable; no devm or async deferral.
2. **“Ownership transferred”?** — No; no list/hash insertion.
3. **Unconditional GET?** — No; contract says conditional (increment only on success). Return value NOT checked → on failure, no ref is held, but PUT is called unconditionally → excess PUT.
4. **goto out between GET and PUT?** — No gotos; all paths after GET reach the PUT before returning.

**VERDICT:** The `pm_runtime_get_sync()` return is ignored; the contract states it increments the counter only on success. The unconditional `pm_runtime_put_sync()` on all post-get paths may decrement a counter that was never incremented if the GET failed, causing a refcount underflow (inconsistent refcounting).

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_get_sync` at L375 return value unchecked; subsequent unconditional `pm_runtime_put_sync` can underflow the counter if GET fails.
```
