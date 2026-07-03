# REAL BUG: drivers/gpu/drm/nouveau/nvkm/subdev/gsp/rm/r535/gsp.c:1778 r535_gsp_fini()

**Confidence**: HIGH | **Counter**: `$->dev->kobj.kref.refcount.refs.counter`

## Reasoning

The “held for device lifetime” pattern applies only to the success path (line 1772), where the metadata is intentionally kept for resume. The error path at line 1764, however, aborts the function and the metadata should be cleaned up; its absence is a real refcount leak.

## Full Response

```
| Line | Return Type | GET Done? (mem_ctor get_device) | PUT Done? (mem_dtor put_device) | Balanced? | Notes |
|------|-------------|----------------------------------|-----------------------------------|-----------|-------|
| 1735 | error (ret) | NO (before get) | N/A | ✅ | nvkm_gsp_sg fail; no get_device |
| 1739 | error (ret) | NO (before get) | N/A | ✅ | nvkm_gsp_radix3_sg fail; no get |
| 1743 | error (ret) | NO (get failed; conditional) | N/A | ✅ | nvkm_gsp_mem_ctor fails → no get_device (contract says conditional_on_path) |
| 1756 | error (ret) | YES (mem_ctor succeeded) | YES (explicit mem_dtor) | ✅ | Cleanup on fbsr->suspend failure |
| 1764 | error (ret) | YES if suspend==true; NO if suspend==false | NO | ❌ LEAK when suspend==true | r535_gsp_rpc_unloading_guest_driver returns error; if suspend was true, mem_ctor succeeded earlier, but no mem_dtor on this path |
| 1772 | success (0) | YES if suspend==true; NO if suspend==false | NO | ⚠️ intentional? | Metadata kept for resume; documented as held for device lifetime. Not a leak when function succeeds. |

**Leak analysis**: Path at line 1764 is reached when `r535_gsp_rpc_unloading_guest_driver()` fails. If `suspend` is true (the `if (suspend)` block executed), `nvkm_gsp_mem_ctor()` succeeded earlier and incremented the device kref via `get_device`. This error path returns immediately without calling `nvkm_gsp_mem_dtor()` to release that reference. The cleanup is only present for `fbsr->suspend` failure, not for this later failure. Therefore, a device reference is leaked on this error path.

No IS_ERR guard, no devm cleanup, no ownership transfer that would release the reference elsewhere (the suspend-resume metadata is not transferred to a long‑lived structure in this error case).

The “held for device lifetime” pattern applies only to the success path (line 1772), where the metadata is intentionally kept for resume. The error path at line 1764, however, aborts the function and the metadata should be cleaned up; its absence is a real refcount leak.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
