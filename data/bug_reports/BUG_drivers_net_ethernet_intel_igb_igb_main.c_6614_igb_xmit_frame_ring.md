# REAL BUG: drivers/net/ethernet/intel/igb/igb_main.c:6614 igb_xmit_frame_ring()

**Confidence**: HIGH | **Counter**: `$->users.refs.counter`

## Reasoning

| Success return (no error) | NETDEV_TX_OK | YES (if TSTAMP) | NO (held for completion/work) | ✅ | balanced externally |

## Full Response

```
| Path | Return Type | GET Done? (extra ref) | PUT Done? (extra ref) | Balanced? | Notes |
|------|-------------|-----------------------|------------------------|-----------|-------|
| Early BUSY (igb_maybe_stop_tx) | NETDEV_TX_BUSY | NO (no get) | N/A  | ✅ | |
| Early BUSY (TX_DISABLED) | NETDEV_TX_BUSY | NO | N/A  | ✅ | |
| goto out_drop (tso < 0) | NETDEV_TX_OK | YES (skb_get if TSTAMP) | YES (dev_kfree_skb_any on first->skb + on ptp_tx_skb) | ❌ RACE | cleanup can free ptp_tx_skb while ptp_tx_work may concurrently free it → double put |
| goto cleanup_tx_tstamp (tx_map fail) | NETDEV_TX_OK | YES (if TSTAMP) | YES (ptp_tx_skb only, first->skb not freed) | ❌ RACE (extra ref) + main ref leak | race on extra ref; main ref missing put but not excess put |
| Success return (no error) | NETDEV_TX_OK | YES (if TSTAMP) | NO (held for completion/work) | ✅ | balanced externally |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`dev_kfree_skb_any(adapter->ptp_tx_skb)` in `cleanup_tx_tstamp` can race with the scheduled `ptp_tx_work`, causing a double free (excess put) on error paths when PTP timestamping is enabled.
```
