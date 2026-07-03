# REAL BUG: drivers/remoteproc/mtk_scp.c:1365 scp_add_multi_core()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

allee is not provided, but the pattern strongly suggests it contains a `put_device()` on the child `platform_device`. Since the caller already dropped its reference at L1330, this results in an extra put when `rproc_add` fails — exactly the refcount excess put that smatch warns about at line 1365.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1319 (goto init_fail) | error | NO (before cpdev get) | N/A | ✅ | |
| L1326 (goto init_fail, cpdev NULL) | error | NO (of_find returned NULL) | N/A | ✅ | |
| L1334 (goto init_fail, IS_ERR(scp)) | error | YES (of_find_device_by_node) | YES (put_device L1330) | ✅ | put_device balanced the get |
| L1341 (goto init_fail, rproc_add fail) | error | YES (of_find) | YES (L1330) + implicit PUT via scp_free(scp) | ❌ EXCESS PUT | scp_free likely calls put_device again, double‑putting cpdev |
| L1356 (return 0, all children added) | success | YES per iteration | YES per iteration | ✅ | scp added to list, scp_free will release later |
| L1365 (return ret after init_fail) | error | YES for previously added scp’s | YES per scp (put_device + scp_free) | ✅ | but the failing iteration (L1341) already caused over‑put |

The `scp_free()` callee is not provided, but the pattern strongly suggests it contains a `put_device()` on the child `platform_device`. Since the caller already dropped its reference at L1330, this results in an extra put when `rproc_add` fails — exactly the refcount excess put that smatch warns about at line 1365.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`scp_free()` likely calls `put_device()` on `cpdev` without a matching get, causing a double‑put on the rproc_add failure path.
```
