# REAL BUG: net/bluetooth/iso.c:1270 iso_listen_bis()

**Confidence**: MEDIUM | **Counter**: `$->refcnt.counter`

## Reasoning

| L58 (success)   | return 0    | YES        | NO (ownership transferred) | ✅        | ref owned by conn, balanced |

## Full Response

```
| Line (local) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|--------------|-------------|-----------|-----------|-----------|-------|
| L20          | error       | NO (before get) | N/A       | ✅        |       |
| L25          | error       | NO (before get) | N/A       | ✅        |       |
| L34 (goto unlock) | error (invalid QoS) | NO (before get) | N/A | ✅        |       |
| L42 (goto unlock) | error (IS_ERR) | NO (get failed) | N/A       | ✅        |       |
| L49 (goto unlock) | error (!conn) | YES        | YES       | ✅        | iso_conn_add failed, ownership not transferred; drop correct |
| L55 (goto unlock) | error (iso_chan_add) | YES | YES       | ❌ EXCESS PUT | iso_conn_add succeeded → ownership transferred → caller should NOT drop |
| L58 (success)   | return 0    | YES        | NO (ownership transferred) | ✅        | ref owned by conn, balanced |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
iso_conn_add transfers ownership of hcon's reference on success; the error path after iso_chan_add at L55 incorrectly calls hci_conn_drop, causing a double-release when the conn is later cleaned up.
```
