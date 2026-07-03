# REAL BUG: net/bluetooth/iso.c:520 iso_connect_cis()

**Confidence**: HIGH | **Counter**: `$->refcnt.counter`

## Reasoning

L509 (success) | fall-through to unlock, return 0 | YES (hcon obtained, iso_conn_add succeeded) | NO (no hci_conn_drop in this function) | ⚠️ (if ownership transferred to iso_conn, caller balance not required; but L491 leak remains) | ref held by iso_conn, but iso_chan_add failure leaks that ref |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L436 | direct return -EHOSTUNREACH | NO (before any get) | N/A | ✅ | |
| L441 | goto unlock (err=-EOPNOTSUPP) | NO | N/A | ✅ | |
| L446 | goto unlock (err=-EINVAL) | NO | N/A | ✅ | |
| L452 | goto unlock (err=-EINVAL) | NO | N/A | ✅ | |
| L458 | goto unlock (err=-ENOBUFS) | NO | N/A | ✅ | |
| L472 | goto unlock (IS_ERR after hci_bind_cis) | NO (get failed) | N/A | ✅ | |
| L480 | goto unlock (IS_ERR after hci_connect_cis) | NO (get failed) | N/A | ✅ | |
| L485 | goto unlock (iso_conn_add fails) | YES (hcon obtained) | YES (hci_conn_drop) | ✅ | |
| L491 | goto unlock (iso_chan_add fails) | YES (hcon obtained, iso_conn_add succeeded) | NO (no hci_conn_drop) | ❌ LEAK | ref held by hcon, never released; iso_conn also leaked |
| L509 (success) | fall-through to unlock, return 0 | YES (hcon obtained, iso_conn_add succeeded) | NO (no hci_conn_drop in this function) | ⚠️ (if ownership transferred to iso_conn, caller balance not required; but L491 leak remains) | ref held by iso_conn, but iso_chan_add failure leaks that ref |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

iso_conn_add succeeds and consumes the hcon reference, but if iso_chan_add subsequently fails, the function returns without removing the iso_conn, leaking both the conn and its held hci_conn reference.
```
