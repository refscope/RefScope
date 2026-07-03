# REAL BUG: drivers/net/wireguard/netlink.c:584 wg_set_device_doit()

**Confidence**: MEDIUM | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

**Request for full verification**: `[NEED_SOURCE] set_peer` to confirm that it indeed acquires a peer reference on some error paths without releasing it.

## Full Response

```
| Line | Return Type | GET Done? (peer) | PUT Done? (peer) | Balanced? | Notes |
|------|-------------|-------------------|-------------------|-----------|-------|
| L479 | error (IS_ERR) | NO (before get) | N/A | ✅ | `wg` invalid, no dev ref taken, no peer get |
| L501 | goto out (cap check) | NO | N/A | ✅ | `dev_put` at `out` releases dev reference; no peer get |
| L513 | goto out (set_port error) | NO | N/A | ✅ | `dev_put` at `out`, no peer get |
| L524 | goto skip_set_private_key | NO (peer get inside block, but skipping block) | N/A | ✅ | skips entire private key block, including peer get; later exits via `out` |
| L533–L535 (inside block, not a return path) | peer found, handled | YES (conditionally) | YES (immediately `wg_peer_put`) | ✅ | Balanced in place |
| L533 (curve25519 fails) | falls through | NO | N/A | ✅ | no peer get |
| L578 (WGDEVICE_A_PEERS) | nla_parse/set_peer error → goto out | YES (if `set_peer` internally calls `wg_pubkey_hashtable_lookup` and fails to release) | NO (if `set_peer` leaks) | ❌ LEAK on error path | Potential leak inside `set_peer`; `out` releases only dev, not peer |
| L578 (WGDEVICE_A_PEERS) | set_peer success → ret=0, out | YES (if `set_peer` acquires and properly stores peer) | YES (through eventual peer teardown, not in this function) | ✅ | Correct ownership transfer if set_peer adds peer to list, peer released later |
| L580 (success) | ret=0 → out | N/A (unless set_peer acquires) | N/A | ✅ | |

**Key observation**: The warning’s counter `$->refcount.refcount.refs.counter` likely tracks a `struct wg_peer` kref. The only `GET`-side contract is `wg_pubkey_hashtable_lookup`, which this function calls only inside the private-key block, and that call is immediately paired with `wg_peer_put`. No other explicit peer get appears in `wg_set_device_doit`. Therefore the inconsistency must arise from `set_peer()`, which is called in the WGDEVICE_A_PEERS loop. On error, the code goes to `out`, which releases only the net_device reference via `dev_put(wg->dev)` but never calls `wg_peer_put()` for any peer reference that `set_peer()` may have acquired. If `set_peer()` internally calls `wg_pubkey_hashtable_lookup` and then fails before successfully integrating the peer (e.g., ownership transfer to the peer list), that reference is leaked — exactly the inconsistency seen at the common exit point `out_nodev`.

**Request for full verification**: `[NEED_SOURCE] set_peer` to confirm that it indeed acquires a peer reference on some error paths without releasing it.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`set_peer()` likely acquires a peer reference via `wg_pubkey_hashtable_lookup` and leaks it on error; the caller’s `goto out` releases only `dev_put(wg->dev)`, not the peer ref, causing an unbalanced kref at the final `out_nodev` return.
```
