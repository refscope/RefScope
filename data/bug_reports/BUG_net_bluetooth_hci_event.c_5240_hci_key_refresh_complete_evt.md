# REAL BUG: net/bluetooth/hci_event.c:5240 hci_key_refresh_complete_evt()

**Confidence**: HIGH | **Counter**: `$->refcnt.counter`

## Reasoning

| L5225 (hci_conn_drop in BT_CONFIG branch, then implicit unlock) | normal finish | NO | YES | ❌ EXCESS PUT | drop without prior hold |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L5204 (goto unlock, conn == NULL) | early return | NO | NO | ✅ | no ref held |
| L5208 (goto unlock, type != LE_LINK) | early return | NO | NO | ✅ | no ref held |
| L5218 (goto unlock after BT_CONNECTED error) | error return before else | NO | YES (hci_conn_drop at L5217) | ❌ EXCESS PUT | drop without prior hold |
| L5225 (hci_conn_drop in BT_CONFIG branch, then implicit unlock) | normal finish | NO | YES | ❌ EXCESS PUT | drop without prior hold |
| L5229–L5231 (else branch: hci_conn_hold → hci_conn_drop, then implicit unlock) | normal finish | YES (L5229) | YES (L5231) | ✅ | locally balanced, net zero |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Two return paths (BT_CONNECTED error and BT_CONFIG) call hci_conn_drop without a preceding hci_conn_hold, causing a refcount underflow (excess put). The else branch’s hold-drop pair is locally balanced, but the other paths leak a reference or underflow.
```
