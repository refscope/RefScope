# REAL BUG: drivers/net/ethernet/broadcom/tg3.c:17029 tg3_get_invariants()

**Confidence**: HIGH | **Counter**: `bridge->dev.kobj.kref.refcount.refs.counter`

## Reasoning

is never released when the loop proceeds to the next device or when the loop exits without a match. This causes leaked references on all but the very first matching device. These leaks persist through all subsequent return paths (both error and success). No ownership transfer, no deferred cleanup.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~16500 (return -EIO) | error | YES (if ICH/5701/EPB loop executed and leaked intermediate bridge refs) | NO | ❌ LEAK | All loops missing `pci_dev_put()` on previous bridge when `continue` or loop ends without match. No put before return. |
| ~17000 (return err after mdio init) | error | YES (same) | NO | ❌ LEAK | Same leak persists; no put. |
| ~17029 (final return err) | success | YES (same) | NO | ❌ LEAK | Function’s end, no cleanup of leaked intermediate refs. |

The loops in the function systematically leak PCI device references obtained via `pci_get_device`. In each loop, the pattern:
```c
bridge = pci_get_device(..., bridge);
if (!bridge) { ... continue; }
...
continue;   /* leak: old bridge not put */
...
pci_dev_put(bridge); break;  /* only put on match */
```
The previous `bridge` is never released when the loop proceeds to the next device or when the loop exits without a match. This causes leaked references on all but the very first matching device. These leaks persist through all subsequent return paths (both error and success). No ownership transfer, no deferred cleanup.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Multiple loops in `tg3_get_invariants()` fail to `pci_dev_put()` the `bridge` on `continue` and loop‑exit paths, leaking refcounts on all return paths after the loops.
```
