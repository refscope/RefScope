# REAL BUG: net/bluetooth/mgmt.c:3731 pair_device()

**Confidence**: HIGH | **Counter**: `$->refcnt.counter`

## Reasoning

| L3690 (unlock) | `err = 0; goto unlock` | YES | NO (no explicit put here) | ⚠️ potential leak, but ownership likely transferred via `cmd->user_data` and callbacks | Not the subject of warning; original reference managed in later callbacks. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3617 (early params check) | `return mgmt_cmd_complete` | NO (before any get) | N/A | ✅ | No lock held, no connection |
| L3622 (early io_cap check) | `return mgmt_cmd_complete` | NO | N/A | ✅ | Same |
| L3629→L3631 (unlock) | `goto unlock` after `!hdev_is_powered` | NO | N/A | ✅ | No get attempted |
| L3636→L3638 (unlock) | `goto unlock` after `hci_bdaddr_is_paired` | NO | N/A | ✅ | No get attempted |
| L3653→L3655 (unlock) | `goto unlock` after `!p` | NO | N/A | ✅ | LE `hci_conn_params_add` fail, `hci_connect_le_scan` not called |
| L3665→L3667 (unlock) | `goto unlock` after `IS_ERR(conn)` | NO (error pointer) | NO | ✅ | Connect call failed, no reference obtained |
| **L3668–3731** (busy check) | `goto unlock` after `hci_conn_drop(conn)` | **YES (expected) / NO (actual if get skipped)** | YES | **❌ EXCESS PUT (UNBALANCED)** | `conn->connect_cfm_cb` set; `hci_conn_drop` called. Warning indicates the underlying `hci_connect_le_scan`/`hci_connect_acl` returned a valid `conn` without incrementing the refcount – causing refcount to go negative. This is the smatch‑flagged line. |
| L3672→L3674 (unlock) | `goto unlock` after `mgmt_pending_add` fail | YES | YES (hci_conn_drop) | ✅ | Reference held, dropped on allocation failure |
| L3690 (unlock) | `err = 0; goto unlock` | YES | NO (no explicit put here) | ⚠️ potential leak, but ownership likely transferred via `cmd->user_data` and callbacks | Not the subject of warning; original reference managed in later callbacks. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the `conn->connect_cfm_cb` busy path (line ~3731), `hci_conn_drop` is called, but the preceding connect function (`hci_connect_le_scan` / `hci_connect_acl`) can return an existing connection without taking an extra reference, causing the put to underflow the refcount. This matches the `refcount excess put` warning at line 3731.
```
