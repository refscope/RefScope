# REAL BUG: net/can/raw.c:545 raw_bind()

**Confidence**: HIGH | **Counter**: `dev->dev_refcnt.refs.counter`

## Reasoning

| **Else branch, err!=0** (dev NULL) | skip if(!err), goto out_put_dev → return err | NO (dev NULL) | dev_put(NULL) → ❌ | ❌ | NULL dev put without get |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L473 (len check) | early return -EINVAL | NO (before any get) | N/A | ✅ | dev never used |
| L474 (can_family check) | early return -EINVAL | NO | N/A | ✅ | |
| L480 (bound && ifindex equal) | goto out → return 0 | NO (no get call) | N/A | ✅ | dev stays NULL |
| L484-486 (dev_get_by_index returns NULL) | goto out → return -ENODEV | NO (get returned NULL) | N/A | ✅ | no ref held |
| L490 (type != ARPHRD_CAN) | goto out_put_dev → return -ENODEV | YES (dev non‑NULL) | YES (dev_put at out_put_dev) | ✅ | |
| L498 (raw_enable_allfilters fails, dev non‑NULL) | goto out_put_dev → return err | YES | YES | ✅ | |
| After if block success (err==0) | fall‑through to out_put_dev → return 0 | YES (dev non‑NULL) | YES (dev_put at out_put_dev) | ✅ | |
| **Else branch, err==0** (dev NULL) | fall‑through, if(!err) executed, then out_put_dev → return 0 | NO (dev NULL) | dev_put(NULL) at out_put_dev → ❌ | ❌ | NULL dev put without get |
| **Else branch, err!=0** (dev NULL) | skip if(!err), goto out_put_dev → return err | NO (dev NULL) | dev_put(NULL) → ❌ | ❌ | NULL dev put without get |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the `addr->can_ifindex == 0` branch, `dev` remains NULL, but the code unconditionally executes `dev_put(dev)` at `out_put_dev`, resulting in a put without a corresponding get.
```
