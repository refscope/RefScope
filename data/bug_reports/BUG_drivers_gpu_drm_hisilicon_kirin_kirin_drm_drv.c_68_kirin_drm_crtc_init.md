# REAL BUG: drivers/gpu/drm/hisilicon/kirin/kirin_drm_drv.c:68 kirin_drm_crtc_init()

**Confidence**: HIGH | **Counter**: `port->kobj.kref.refcount.refs.counter`

## Reasoning

| L68  | success | YES (port non-NULL) | YES (of_node_put at L54) | ❌ (excess put, use-after-free) | Same premature PUT; crtc continues to use freed port node |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L52  | error (port NULL) | NO (get failed) | NO  | ✅ | of_get_child_by_name returned NULL, no reference taken, safe return |
| L63  | error (crtc init fail) | YES (port non-NULL) | YES (of_node_put at L54) | ❌ (excess put, use-after-free) | PUT released reference but `crtc->port = port` still holds pointer; ref now zero → dangling |
| L68  | success | YES (port non-NULL) | YES (of_node_put at L54) | ❌ (excess put, use-after-free) | Same premature PUT; crtc continues to use freed port node |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
of_node_put called immediately after of_get_child_by_name, leaving crtc->port a dangling pointer with zero refcount — an excess put that should not occur while the node is still in use.
```
