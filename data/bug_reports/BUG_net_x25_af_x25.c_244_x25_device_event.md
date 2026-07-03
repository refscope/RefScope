# REAL BUG: net/x25/af_x25.c:244 x25_device_event()

**Confidence**: HIGH | **Counter**: `$->dev_refcnt.refs.counter`

## Reasoning

If `x25_link_device_up()` (which calls `dev_hold`) was never invoked (e.g., because the X.25 device was registered before the notifier was active, or if a type change sequence missed the up), the refcount is decremented without a matching increment, resulting in the observed “refcount excess put”.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L209 (early return) | NOTIFY_DONE | NO (before get) | NO | ✅ | netns mismatch, no dev ref ops |
| L212 (NETDEV_REGISTER) | break → NOTIFY_DONE | YES (x25_link_device_up) | NO | ⚠️ | intentional; put delayed to later event |
| L213 (NETDEV_POST_TYPE_CHANGE) | break → NOTIFY_DONE | YES | NO | ⚠️ | same as above |
| L216–L221 (NETDEV_DOWN) | break → NOTIFY_DONE | NO | NO | ✅ | only neighbor refs, no dev_hold/put |
| L222 (NETDEV_PRE_TYPE_CHANGE) | break → NOTIFY_DONE | NO | **YES** (x25_link_device_down) | ❌ | **excess put** if no prior GET |
| L223 (NETDEV_UNREGISTER) | break → NOTIFY_DONE | NO | **YES** (x25_link_device_down) | ❌ | **excess put** if  prior GET missing |
| L227–L235 (NETDEV_CHANGE) | break → NOTIFY_DONE | NO | NO | ✅ | no dev ref ops |

**Pre-Verdict Checklist:**
- “Held for lifetime” only applies to success; N/A here because the bug is excess put on a path that does PUT unconditionally.
- Ownership transfer: N/A; the device ref is held by the link-up state, but the PUT occurs without a check.
- Unconditional GET? No, GET is not on the UNREGISTER path. The PUT is unconditional; GET is external and may not have happened.
- goto out: none; all paths are straight-line to the final return.

The UNREGISTER / PRE_TYPE_CHANGE paths unconditionally call `x25_link_device_down()`, which performs a `dev_put` on the netdev refcount. If `x25_link_device_up()` (which calls `dev_hold`) was never invoked (e.g., because the X.25 device was registered before the notifier was active, or if a type change sequence missed the up), the refcount is decremented without a matching increment, resulting in the observed “refcount excess put”.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`x25_link_device_down` does unconditional `dev_put` on UNREGISTER / PRE_TYPE_CHANGE paths, but prior `x25_link_device_up` (which does `dev_hold`) is not guaranteed, causing an excess put when the notifier misses the initial registration.
```
