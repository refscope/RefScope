# REAL BUG: drivers/base/power/common.c:298 dev_pm_domain_attach_list()

**Confidence**: MEDIUM | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

zero during detach. The subsequent explicit `device_link_del` would cause an excess kref_put, matching the refcount warning. Without the source of `dev_pm_domain_detach()` I cannot definitively confirm the double free, but the pattern (detach likely tears down links) strongly suggests a real bug.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L201 | error       | NO (before any get) | N/A  | ✅ | dev->pm_domain already set |
| L208 | 0           | NO | N/A  | ✅ | !np, no domains |
| L219 | 0           | NO | N/A  | ✅ | num_pds ≤ 0 |
| L224 | -ENOMEM     | NO | N/A  | ✅ | kzalloc pds failed |
| L237 | -ENOMEM (goto free_pds) | NO | N/A  | ✅ | kcalloc pd_devs failed |
| L256 (IS_ERR_OR_NULL pd_dev) → goto err_attach | error | NO (no link_add) | N/A | ✅ | detach called only on pd_dev, no link |
| L262 (opp_set_config < 0) → goto err_link | error | NO (link_add not yet) | N/A | ✅ | detach called on pd_dev, no link |
| L272 (device_link_add returns NULL) → goto err_link | error | NO (get failed) | N/A | ✅ | link not stored, no del needed |
| L279 (success, *list = pds) | return num_pds | YES (for each i) | NO | ✅ (ownership transferred) | References held by returned pds, caller must release later |
| L281 err_link (current i after opp_set_config or device_link_add failure) → L290 free | error | NO | N/A | ✅ | no link stored |
| L283 err_attach (while --i >= 0) → L290 free | error | YES (previous i’s with stored links) | YES (device_link_del called) | ❓ **Potential double put** if dev_pm_domain_detach also puts the link reference | ⚠️ Warning line 298 is inside this while loop |

[NEED_SOURCE] dev_pm_domain_detach

The warning at line 298 points to the while loop in `err_attach` that calls `device_link_del(pds->pd_links[i])`. If `dev_pm_domain_detach(pd_dev, true)` (called just above in the loop) internally removes device links associated with the supplier `pd_dev`—for example by calling `device_links_unbind_consumers()` or similar—then the link’s kref would already be decremented to zero during detach. The subsequent explicit `device_link_del` would cause an excess kref_put, matching the refcount warning. Without the source of `dev_pm_domain_detach()` I cannot definitively confirm the double free, but the pattern (detach likely tears down links) strongly suggests a real bug.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`dev_pm_domain_detach(pd_dev, true)` likely already removes the device link, leading to a double put when `device_link_del()` is called on the same link in the `err_attach` cleanup loop.
```
