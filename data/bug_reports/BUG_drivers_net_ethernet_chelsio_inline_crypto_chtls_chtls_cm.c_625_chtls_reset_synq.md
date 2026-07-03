# REAL BUG: drivers/net/ethernet/chelsio/inline_crypto/chtls/chtls_cm.c:625 chtls_reset_synq()

**Confidence**: HIGH | **Counter**: `child->sk_refcnt.refs.counter`

## Reasoning

an unconditional PUT according to the contract. Each iteration gets one reference (sock_hold) but puts twice (reset_listen_child + sock_put), causing net -1 per child. This leads to refcount underflow on `child->sk_refcnt`. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L641 (after while) | void return | YES (sock_hold per child) | YES (sock_put per child) + PUT (reset_listen_child) | ❌ EXCESS PUT | reset_listen_child is an unconditional PUT according to the contract. Each iteration gets one reference (sock_hold) but puts twice (reset_listen_child + sock_put), causing net -1 per child. This leads to refcount underflow on `child->sk_refcnt`. |

[NEED_SOURCE] reset_listen_child  
[NEED_SOURCE] cleanup_syn_rcv_conn  

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
The contract marks `reset_listen_child()` as an unconditional PUT. Combined with the explicit `sock_put(child)`, each loop iteration releases two references for the one acquired by `sock_hold(child)`, creating a refcount excess put — exactly the reported warning.
```
