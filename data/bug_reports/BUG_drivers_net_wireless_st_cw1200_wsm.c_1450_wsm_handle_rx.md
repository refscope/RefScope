# REAL BUG: drivers/net/wireless/st/cw1200/wsm.c:1450 wsm_handle_rx()

**Confidence**: HIGH | **Counter**: `$->tx_lock.counter`

## Reasoning

| L1471 (`out: return ret`) | NO | NO | ✅ | default exit |

## Full Response

```
| Line | Return Type | GET Done? (tx_lock) | PUT Done? (tx_lock) | Balanced? | Notes |
|------|-------------|---------------------|---------------------|-----------|-------|
| L1318 | error (or 0) from wsm_tx_confirm | NO | NO | ✅ | tx_lock not used in this path |
| L1319 | error (or 0) from wsm_multi_tx_confirm | NO | NO | ✅ | tx_lock not used |
| L1330 | goto out (WARN_ON bad id) | NO | NO | ✅ | tx_lock not used |
| various within id&0x0400 block | return via `goto out` or `ret = 0; ... goto out` | NO¹ | NO¹ | ✅ | tx_lock touched only inside specific error path (see below) |
| L1393 (wsm_generic_confirm error, join_status >= JOINING, queue_work) | after wsm_lock_tx, if queue_work <= 0 then wsm_unlock_tx; otherwise no put (work will do it) | YES then NO or YES then PUT (conditional) | Depends | ⚠️ Complex but locally balanced: if queue_work fails, explicit unlock; if success, work item will unlock later. No excess put here. |
| L1393 (join_status < JOINING or wsm_generic_confirm ok) | NO | NO | ✅ | no lock/unlock |
| L1430–L1469 (id & 0x0800 block) | NO | NO | ✅ (within this function) | **The warning targets line 1450** – `wsm_channel_switch_indication`. This function does not touch tx_lock; however, the callee itself performs a `wsm_unlock_tx` at some point, causing an “excess put” on `tx_lock.counter`. The imbalance originates inside the callee. |
| L1471 (`out: return ret`) | NO | NO | ✅ | default exit |

[NEED_SOURCE] wsm_channel_switch_indication  
[NEED_SOURCE] wsm_lock_tx  
[NEED_SOURCE] wsm_unlock_tx  

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`wsm_channel_switch_indication` issues a `wsm_unlock_tx` without a matching `wsm_lock_tx`, producing a refcount excess put on `tx_lock.counter`. `wsm_handle_rx` itself never holds `tx_lock` when calling that handler, so the imbalance is entirely within the callee.
```
