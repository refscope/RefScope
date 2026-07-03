# REAL BUG: drivers/usb/typec/altmodes/displayport.c:817 dp_altmode_probe()

**Confidence**: HIGH | **Counter**: `plug->dev.kobj.kref.refcount.refs.counter`

## Reasoning

| L781 | error (-ENOMEM) | YES (if plug ≠ NULL) | YES | ✅ | `typec_altmode_put_plug(plug)` called before return. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L767 | error (-EPROTO) | YES (if plug ≠ NULL) | NO  | ❌ LEAK | Early return before any put; plug ref acquired but not released. |
| L774 | error (-ENODEV) | YES (if plug ≠ NULL) | YES | ✅ | `typec_altmode_put_plug(plug)` called before return. |
| L781 | error (-ENOMEM) | YES (if plug ≠ NULL) | YES | ✅ | `typec_altmode_put_plug(plug)` called before return. |
| L817 | success (0)     | YES (if plug ≠ NULL) | NO (ownership transferred) | ✅ | plug stored in `dp->plug_prime`, released in `dp_altmode_remove()`. |

**PRE-VERDICT CHECKLIST**  
1. “Held for device lifetime”? Only applies to success return (L817); early error path (L767) is **not** covered.  
2. “Ownership transferred”? For L767: no, pointer never stored → no cleanup → must put.  
3. Unconditional GET? `typec_altmode_get_plug()` returns NULL or non‑NULL; if non‑NULL, reference is taken. L767 leaks that reference when non‑NULL.  
4. goto out? None – simple return, no hidden label.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`typec_altmode_get_plug()` at L763 acquires a reference if `plug` is non‑NULL. The immediate `return -EPROTO` at L767 does not call `typec_altmode_put_plug(plug)`, leaking the reference on every call where a plug exists.
```
