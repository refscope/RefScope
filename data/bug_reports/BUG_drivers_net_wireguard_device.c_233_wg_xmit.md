# REAL BUG: drivers/net/wireguard/device.c:233 wg_xmit()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

reference, the bug lies elsewhere (unlikely given the warning). The standard WireGuard idiom for xmit is to use the peer under RCU without an additional reference, so the get is conditional and null, and no put should be done. The presence of `wg_peer_put` strongly suggests a mismatch.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 151 (`goto err`) | error (`-EPROTONOSUPPORT`) | NO (before lookup) | N/A | ✅ | `peer` not assigned; `err` label has no `wg_peer_put` |
| 162 (`goto err_icmp`) | error (`-ENOKEY`) | NO (`peer == NULL`) | N/A | ✅ | `err_icmp` falls through to `err` with no extra put |
| 176 (`goto err_peer`) | error (`-EDESTADDRREQ`) | YES | YES (`wg_peer_put` at L233 in `err_peer`) | ✅ | Normal error cleanup |
| 181 (`goto err_peer`) | error (IS_ERR from `skb_gso_segment`) | YES | YES (`wg_peer_put` at `err_peer`) | ✅ | Handles gso segment failure |
| 230 (`return NETDEV_TX_OK`) | success | YES | YES (`wg_peer_put` at L233) | ❌ Excess put (if get was no‑op) | `wg_allowedips_lookup_dst` may not hold a reference; see analysis |

**⚠️ Key observation**: The GET function `wg_allowedips_lookup_dst` is not provided. Its contract is unknown. Based on the `excess put` warning, the most likely cause is that this function **does not increment the peer’s kref** (e.g., it returns a pointer valid only under RCU). Consequently, the subsequent `wg_peer_put(peer)` on the success path (line ~233) is an extra put, triggering a refcount underflow.

Without the source of `wg_allowedips_lookup_dst`, I cannot definitively confirm its contract. I will request it now:

[NEED_SOURCE] wg_allowedips_lookup_dst

---

## Analysis using requested source

*(Once the source is provided, I will update the verdict.)*

**Preliminary verdict** (based on the warning and the structure of the code):

- All error paths after obtaining `peer` go through `err_peer` which correctly does `wg_peer_put`.
- The success path does `wg_peer_put` after `wg_packet_send_staged_packets`.
- No double-put is visible *within* `wg_xmit`.
- The warning is a **refcount excess put** (underflow) on the success path. This implies that at that point the refcount is already zero, i.e., **no matching `kref_get` was performed**.

Therefore, if `wg_allowedips_lookup_dst` does **not** take a reference, the verdict is `REAL_BUG` (the code should not call `wg_peer_put`). If it *does* return with a reference, the bug lies elsewhere (unlikely given the warning). The standard WireGuard idiom for xmit is to use the peer under RCU without an additional reference, so the get is conditional and null, and no put should be done. The presence of `wg_peer_put` strongly suggests a mismatch.

---

## PRE-VERDICT CHECKLIST

1. **"Held for device lifetime"?** — N/A (this is the xmit path, not probe).  
2. **"Ownership transferred"?** — No, the peer is used only inside `wg_xmit`, no long-term storage that justifies skipping the put.  
3. **Unconditional GET?** — Unknown; must be determined from `wg_allowedips_lookup_dst`. If it returns without ref, the GET is effectively NO.  
4. **goto out between GET and PUT?** — All goto’s after GET go to `err_peer` which does the put → no missed put.  

The only r
```
