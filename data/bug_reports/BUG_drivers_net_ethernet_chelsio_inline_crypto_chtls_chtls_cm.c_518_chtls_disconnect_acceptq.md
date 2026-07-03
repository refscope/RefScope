# REAL BUG: drivers/net/ethernet/chelsio/inline_crypto/chtls/chtls_cm.c:518 chtls_disconnect_acceptq()

**Confidence**: HIGH | **Counter**: `child->sk_refcnt.refs.counter`

## Reasoning

loop takes if‑branch: sock_put(child) at L535) | Code appears balanced, but ordering is broken. | reqsk_put(req) at L527 may release the request and drop the reference to child **before** sock_hold(child), making the child dangling. The subsequent sock_put triggers the excess‑put warning. |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| End of function (implicit) | void | YES (if loop takes if‑branch: sock_hold(child) at L528) | YES (if loop takes if‑branch: sock_put(child) at L535) | Code appears balanced, but ordering is broken. | reqsk_put(req) at L527 may release the request and drop the reference to child **before** sock_hold(child), making the child dangling. The subsequent sock_put triggers the excess‑put warning. |
```

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  

`reqsk_put(req)` at L527 can free the request sock and, via its destructor, release the child sock’s reference. Doing `sock_hold(child)` afterwards operates on a potentially freed socket, leading to a use‑after‑free and causing the `sock_put` at L535 to underflow the (already zero) refcount – exactly the “excess put” reported. The hold must be moved before `reqsk_put(req)`.
```
