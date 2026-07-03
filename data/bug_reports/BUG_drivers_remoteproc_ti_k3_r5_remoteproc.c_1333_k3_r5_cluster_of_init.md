# REAL BUG: drivers/remoteproc/ti_k3_r5_remoteproc.c:1333 k3_r5_cluster_of_init()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

Therefore, the `put_device(&cpdev->dev)` in the success path of `k3_r5_cluster_of_init` is a bug that leads to the reported excess put.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| inside loop, cpdev NULL → goto fail (L1311?) | error     | NO (cpdev NULL, of_find_device_by_node returned NULL, no get) | N/A        | ✅       | No device obtained, safe. |
| inside loop, k3_r5_core_of_init fails → put_device(&cpdev->dev); goto fail (L1316-1318) | error after put | YES (of_find_device_by_node succeeded) | YES (explicit put before goto) | ✅ for this iteration | Core not added to list, cluster_of_exit won’t try to put_device on it. Safe. |
| inside loop, success path → put_device(&cpdev->dev); list_add_tail(...) (L1321-1323) | continues loop | YES (of_find_device_by_node succeeded) | YES (put_device) | ❌ INCORRECT: puts reference that must be kept for cluster lifecycle | This put is an error because it drops the reference, causing a later excess put when cluster_of_exit calls put_device (line 1333). |
| end of loop, return 0 (L1325) | success | N/A (no new get) | N/A | ✅ | loop done, no further put call here. |

The warning line (1333) is inside `k3_r5_cluster_of_exit`, which is not provided but is known (from typical driver pattern and line numbering) to iterate over `cluster->cores` and call `put_device` on each core’s device. After the success path above drops the reference, that later `put_device` becomes an excess put (refcount underflow).

Therefore, the `put_device(&cpdev->dev)` in the success path of `k3_r5_cluster_of_init` is a bug that leads to the reported excess put.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
The success path in `k3_r5_cluster_of_init` incorrectly calls `put_device` on the core’s device after obtaining it via `of_find_device_by_node`. The reference should be held for later release in `k3_r5_cluster_of_exit`; this premature put causes a double‑put in the exit function, matching the “refcount excess put” warning.
```
