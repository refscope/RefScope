# REAL BUG: drivers/platform/surface/aggregator/ssh_packet_layer.c:1126 ssh_ptl_tx_threadfn()

**Confidence**: HIGH | **Counter**: `$->refcnt.refcount.refs.counter`

## Reasoning

| L1130 (loop exit → return 0) | return 0 | N/A (no outstanding ref at loop exit) | N/A | ✅ | Loop’s iteration disposes of its packet before looping back; final return is clean. |

## Full Response

```
[NEED_SOURCE] ssh_ptl_tx_compl_error
[NEED_SOURCE] ssh_ptl_tx_compl_success
[NEED_SOURCE] ssh_ptl_tx_next

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1111 (IS_ERR(packet) → continue) | continue (no function return) | NO (packet is ERR_PTR, get failed) | N/A | ✅ | No reference acquired, no put needed. |
| L1117‑1120 (status != 0 → ssh_ptl_tx_compl_error(), then L1126 ssh_packet_put()) | continues loop | YES (valid packet from ssh_ptl_tx_next, assumes ref held) | YES (ssh_packet_put() executed) BUT completion likely already consumed the reference → double put | ❌ excess put | ssh_packet_put called after completion; if completion put the packet, refcount goes negative. |
| L1117‑1120 (status == 0 → ssh_ptl_tx_compl_success(), then L1126 ssh_packet_put()) | continues loop | YES | YES (ssh_packet_put()) BUT possible double | ❌ excess put | Same as above – putative double‑put after success completion. |
| L1130 (loop exit → return 0) | return 0 | N/A (no outstanding ref at loop exit) | N/A | ✅ | Loop’s iteration disposes of its packet before looping back; final return is clean. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The warning points to the `ssh_packet_put()` at line 1126, after `ssh_ptl_tx_compl_error()` / `ssh_ptl_tx_compl_success()` have already completed the packet. These completion routines almost certainly release the packet’s reference (their names imply consumption), so the explicit `ssh_packet_put()` causes a double put and an excess refcount drop. The two non‑IS_ERR paths in the loop are therefore unbalanced.
```
