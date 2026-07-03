# REAL BUG: net/ipv6/tcp_ipv6.c:1981 tcp_v6_rcv()

**Confidence**: HIGH | **Counter**: `$->__sk_common.skc_refcnt.refs.counter`

## Reasoning

| 1979 fallthrough → 1981 goto discard_it (TCP_TW_SUCCESS) | goto discard_it | YES | **NO** | ❌ **LEAK** | fallthrough after `;`, no put |

## Full Response

```
| Line | Return Type | GET Done? (twsk ref) | PUT Done? (twsk_put) | Balanced? | Notes |
|------|-------------|-----------------------|----------------------|-----------|-------|
| 1932 | goto discard_it (xfrm fail) | YES | YES (inet_twsk_put) | ✅ | |
| 1939 | goto csum_error -> discard_it | YES | YES (inet_twsk_put) | ✅ | |
| 1961 | goto process (sk2 found, TCP_TW_SYN) | YES | YES (inet_twsk_deschedule_put) | ✅ | refcounted=false, left timewait |
| 1977 | goto discard_it (TCP_TW_RST) | YES | YES (inet_twsk_deschedule_put) | ✅ | |
| 1966 break → 1981 goto discard_it (TCP_TW_SYN, drop_reason) | goto discard_it | YES | **NO** | ❌ **LEAK** | break from switch, no put |
| 1973 break → 1981 goto discard_it (TCP_TW_ACK / TCP_TW_ACK_OOW) | goto discard_it | YES | **NO** | ❌ **LEAK** | break from switch, no put |
| 1979 fallthrough → 1981 goto discard_it (TCP_TW_SUCCESS) | goto discard_it | YES | **NO** | ❌ **LEAK** | fallthrough after `;`, no put |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`inet6_lookup_skb` acquires a reference on the timewait socket; `TCP_TW_SYN` (with drop_reason), `TCP_TW_ACK`, `TCP_TW_ACK_OOW` and `TCP_TW_SUCCESS` paths reach `goto discard_it` at line 1981 without calling `inet_twsk_put`, leaking the refcount.
```
