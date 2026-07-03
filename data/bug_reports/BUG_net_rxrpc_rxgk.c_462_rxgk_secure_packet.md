# REAL BUG: net/rxrpc/rxgk.c:462 rxgk_secure_packet()

**Confidence**: HIGH | **Counter**: `$->usage.refs.counter`

## Reasoning

| L462 | return -EPERM (default) | YES | YES (rxgk_put at L461) | ❌ IMBALANCE | 2 incs, 1 dec → leaked reference |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L440 | IS_ERR (error) | NO | N/A | ✅ | rxgk_get_key returned ERR_PTR, no reference acquired |
| L445 | ret < 0 (error) | YES (rxgk_get_key succeeded) | YES (rxgk_put at L444) | ❌ IMBALANCE | GET contract: 2 refcount_inc; PUT contract: 1 refcount_dec. One extra ref leaked. |
| L455 | return 0 (PLAIN) | YES | YES (rxgk_put at L453) | ❌ IMBALANCE | Same imbalance: 2 incs, 1 dec → leak |
| L457 | return rxgk_secure_packet_integrity (AUTH) | YES (ownership transfer) | YES (called function does unconditional rxgk_put) | ❌ IMBALANCE | Called function does 1 dec → still 1 ref leaked |
| L459 | return rxgk_secure_packet_encrypted (ENCRYPT) | YES (ownership transfer) | YES (called function does unconditional rxgk_put) | ❌ IMBALANCE | Same as above |
| L462 | return -EPERM (default) | YES | YES (rxgk_put at L461) | ❌ IMBALANCE | 2 incs, 1 dec → leaked reference |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

rxgk_get_key performs two refcount_inc operations (contract), but every return path that acquired the reference releases at most one ref (via rxgk_put or transfer to a function that does one put). The second incremented reference is never released, causing a permanent refcount leak.
```
