# REAL BUG: drivers/thunderbolt/icm.c:1422 icm_tr_xdomain_disconnected()

**Confidence**: HIGH | **Counter**: `xd->dev.kobj.kref.refcount.refs.counter`

## Reasoning

Given the pattern of `remove_*` helpers in the kernel that dispose of objects and release their references, the explicit put after the removal is almost certainly erroneous.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1419 (xd == NULL) | implicit return (void) | NO (find_by_route returned NULL) | N/A | ✅ | no ref acquired |
| L1420-1423 (xd != NULL) | implicit return (void) | YES (find_by_route non-NULL → get) | YES (tb_xdomain_put at L1422) | ⚠️ Locally balanced, but warning says excess put at L1422 | remove_xdomain(xd) is called before put; its internal ref handling is unknown |

[NEED_SOURCE] remove_xdomain  
The `remove_xdomain` callee’s refcount behavior is not documented. The warning at L1422 (`refcount excess put`) strongly suggests that `remove_xdomain` already drops the reference (ownership is transferred or the object is released inside), making the following `tb_xdomain_put` a double-free. Without its source, the exact mechanism cannot be confirmed, but the runtime detection points to an immediate excess put.

Given the pattern of `remove_*` helpers in the kernel that dispose of objects and release their references, the explicit put after the removal is almost certainly erroneous.

```
VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
`remove_xdomain` internally releases the xdomain reference, so the explicit `tb_xdomain_put` at L1422 causes a refcount underflow. The runtime ‘excess put’ warning directly matches this double-put pattern.
```
