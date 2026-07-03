# REAL BUG: drivers/thunderbolt/icm.c:1027 icm_fr_xdomain_disconnected()

**Confidence**: HIGH | **Counter**: `xd->dev.kobj.kref.refcount.refs.counter`

## Reasoning

rmal void return | YES (tb_xdomain_find_by_uuid succeeded, reference held) | YES (tb_xdomain_put at L1027) | ❌ EXCESS PUT | **remove_xdomain()** likely already dropped the initial reference, causing `tb_xdomain_put()` to underflow — confirmed by runtime `refcount excess put` warning. Double put. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| End of function, xd == NULL | Normal void return | NO (tb_xdomain_find_by_uuid returned NULL) | N/A | ✅ | No reference acquired, nothing to release. |
| End of function, xd != NULL | Normal void return | YES (tb_xdomain_find_by_uuid succeeded, reference held) | YES (tb_xdomain_put at L1027) | ❌ EXCESS PUT | **remove_xdomain()** likely already dropped the initial reference, causing `tb_xdomain_put()` to underflow — confirmed by runtime `refcount excess put` warning. Double put. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

tb_xdomain_find_by_uuid() returns a reference; remove_xdomain() appears to internally release that reference (or the device’s base reference), making the subsequent tb_xdomain_put() an extra decrement that triggers an underflow. The runtime warning directly confirms the excess put on line 1027.
```
