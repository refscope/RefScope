# REAL BUG: net/bluetooth/hci_event.c:3549 hci_auth_complete_evt()

**Confidence**: HIGH | **Counter**: `$->refcnt.counter`

## Reasoning

**The warning at line 3549 corresponds to the `hci_conn_drop(conn)` in the `BT_CONFIG` else branch (snippet L3524).** That drop has no preceding `hci_conn_hold` in the same path, making it an **excess put** on the connection’s refcount.

## Full Response

```
## Path Table (all return paths in `hci_auth_complete_evt`)

| Line (snippet) | Actual Path Description                       | GET Done? (hci_conn_hold) | PUT Done? (hci_conn_drop) | Balanced? | Notes                                                                          |
|----------------|-----------------------------------------------|---------------------------|---------------------------|-----------|--------------------------------------------------------------------------------|
| L3499          | `goto unlock` (conn == NULL)                  | NO                        | N/A                       | ✅         | no connection at all                                                           |
| L3514–L3520    | `conn->state == BT_CONFIG` → SSP encrypt path | NO                        | NO                        | ✅         | no hold/drop; command sent, no ref change                                      |
| L3522–L3524    | `conn->state == BT_CONFIG` → else branch      | NO                        | YES (`hci_conn_drop`)     | ❌         | **Excess put** – no matching get anywhere in this function                      |
| L3527–L3531    | `conn->state != BT_CONFIG`                    | YES (`hci_conn_hold`)     | YES (`hci_conn_drop`)     | ✅         | hold/drop pair cancels out; no net change                                      |

**The warning at line 3549 corresponds to the `hci_conn_drop(conn)` in the `BT_CONFIG` else branch (snippet L3524).** That drop has no preceding `hci_conn_hold` in the same path, making it an **excess put** on the connection’s refcount.

---

## VERDICT: REAL_BUG

**CONFIDENCE: HIGH**

In the `hci_auth_complete_evt` function, when `conn->state == BT_CONFIG` and the SSP-enabled condition is false, the code unconditionally calls `hci_conn_drop(conn)` without ever calling `hci_conn_hold` on that path. This releases a reference that was never acquired within the function, causing the connection’s refcount to underflow (negative). The `excess put` warning correctly identifies this missing-get bug.
```
