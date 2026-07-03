# REAL BUG: drivers/xen/gntdev-dmabuf.c:473 dmabuf_exp_from_refs()

**Confidence**: MEDIUM | **Counter**: `map->users.refs.counter`

## Reasoning

*map’s* reference count but does **not** undo the user mapping. Therefore, two error paths (line 455 and line 463) leak the `users.refs` reference. The success path (line 466) is fine because the dmabuf release handler will unmap later. The early IS_ERR return is safe as no mapping was attempted.

## Full Response

```
## Path Table

| Line | Return Type | GET (gntdev_map_grant_pages) | PUT (unmap / users.refs decrement) | Balanced? | Notes |
|------|-------------|-------------------------------|--------------------------------------|-----------|-------|
| L439 | error       | NO (before map call)           | N/A                                  | ✅         | map allocation failed; no mapping done |
| L466 | success     | YES                            | YES (dmabuf cleanup deferred)        | ✅         | dmabuf takes ownership; release callback does unmap |
| L455 | goto out    | ⚠️ YES (mapping likely incremented users.refs even on partial failure) | NO (only dmabuf_exp_remove_map, which does not unmap/decrement users.refs) | ❌ LEAK | gntdev_map_grant_pages may increment users.refs before failing; no unmap called |
| L463 | goto out    | YES (mapping succeeded earlier) | NO                                   | ❌ LEAK | mapping was done, but error path only calls remove_map; users.refs remains elevated |

**Reasoning**: `gntdev_map_grant_pages` maps the grant pages and increments the `map->users.refs.counter`. On error, the function must either unmap the pages (which decrements `users.refs`) or at least call the appropriate put. The cleanup label `out:` only calls `dmabuf_exp_remove_map`, which removes the map from the device list and calls `gntdev_put_map` — that decrements the *map’s* reference count but does **not** undo the user mapping. Therefore, two error paths (line 455 and line 463) leak the `users.refs` reference. The success path (line 466) is fine because the dmabuf release handler will unmap later. The early IS_ERR return is safe as no mapping was attempted.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
```
