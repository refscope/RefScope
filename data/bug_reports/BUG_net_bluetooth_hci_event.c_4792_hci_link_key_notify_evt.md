# REAL BUG: net/bluetooth/hci_event.c:4792 hci_link_key_notify_evt()

**Confidence**: HIGH | **Counter**: `$->refcnt.counter`

## Reasoning

| L4772 | goto unlock (debug key removal) | YES (already counted) | YES (already dropped) | ✅ | net zero |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L4737 | goto unlock (conn NULL) | NO (before hold) | N/A (no drop) | ✅ | no reference taken |
| L4744 | goto unlock (null link key) | NO (hold not yet called) | YES (hci_conn_drop at L4743) | ❌ EXCESS PUT | drop without hold → refcount underflow |
| L4755 | goto unlock (HCI_MGMT not set) | YES (hold at L4747, drop at L4749) | YES (already dropped) | ✅ | net zero |
| L4759 | goto unlock (hci_add_link_key fails) | YES (already counted) | YES (already dropped) | ✅ | net zero |
| L4772 | goto unlock (debug key removal) | YES (already counted) | YES (already dropped) | ✅ | net zero |
| L4780 | fallthrough unlock | YES (already counted) | YES (already dropped) | ✅ | net zero |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
In the NULL link key early-return path (L4742-4744) `hci_conn_drop()` is called without a preceding `hci_conn_hold()`, causing an unbalanced put that triggers a refcount underflow. The hold/drop pair at L4747/4749 is balanced for all subsequent paths.
```
