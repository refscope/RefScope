# REAL BUG: net/netlink/af_netlink.c:1359 netlink_unicast()

**Confidence**: HIGH | **Counter**: `sk->sk_refcnt.refs.counter`

## Reasoning

| L1359 | success      | YES (reference was acquired) | **EXTRA** (netlink_attachskb already put, then netlink_sendskb puts again) | ❌ **EXCESS PUT** | netlink_attachskb contract: unconditional sock_put; netlink_sendskb contract: unconditional sock_put → double-put |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1341 | error (IS_ERR) | NO (get failed) | N/A | ✅ | netlink_getsockbyportid returned error → no ref held |
| L1344 | return (kernel) | YES | YES (via netlink_unicast_kernel sock_put) | ✅ | netlink_unicast_kernel contract: unconditional sock_put |
| L1350 | error (filter) | YES | YES (sock_put) | ✅ | explicit sock_put for the reference |
| L1355 | goto retry   | YES (but old ref dropped by netlink_attachskb) | YES (netlink_attachskb unconditional sock_put) | ✅ | netlink_attachskb dropped old ref; new ref will be acquired at retry |
| L1357 | error (err)  | YES (reference held before call) | YES (netlink_attachskb unconditional sock_put) | ✅ | netlink_attachskb dropped ref regardless of error |
| L1359 | success      | YES (reference was acquired) | **EXTRA** (netlink_attachskb already put, then netlink_sendskb puts again) | ❌ **EXCESS PUT** | netlink_attachskb contract: unconditional sock_put; netlink_sendskb contract: unconditional sock_put → double-put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

netlink_attachskb unconditionally drops the socket reference (per contract). On the success path (err == 0) the code returns via netlink_sendskb, which also unconditionally calls sock_put, causing a refcount underflow at line 1359.
```
```
