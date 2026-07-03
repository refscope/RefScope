# REAL BUG: net/bluetooth/l2cap_sock.c:1441 l2cap_sock_shutdown()

**Confidence**: HIGH | **Counter**: `sk->sk_refcnt.refs.counter`

## Reasoning

| ~L1420| fallthrough to shutdown_matched| YES                     | YES (sock_put at shutdown_matched)  | ✅        | normal path after L2CAP close and linger wait                         |

## Full Response

```
```
| Line | Return Type                     | GET Done?               | PUT Done?                           | Balanced? | Notes                                                                 |
|------|---------------------------------|-------------------------|-------------------------------------|-----------|-----------------------------------------------------------------------|
| L1350| return 0                        | NO (before get)         | N/A                                 | ✅        | early return, sk is NULL                                              |
| L1356| goto shutdown_already           | NO (before get)         | N/A                                 | ✅        | shutdown already set, no sock_hold yet                                |
| L1368| goto shutdown_already           | YES (sock_hold at L1362)| NO (shutdown_already has no sock_put)| ❌ LEAK   | chan is NULL, skips shutdown_matched where sock_put would happen     |
| L1379| goto shutdown_matched           | YES                     | YES (sock_put at shutdown_matched)  | ✅        | after __l2cap_wait_ack matched shutdown                               |
| ~L1393| goto shutdown_matched          | YES                     | YES (sock_put at shutdown_matched)  | ✅        | RCV_SHUTDOWN handled, matched                                         |
| ~L1420| fallthrough to shutdown_matched| YES                     | YES (sock_put at shutdown_matched)  | ✅        | normal path after L2CAP close and linger wait                         |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
sock_hold() unconditionally increments sk->sk_refcnt. When the subsequent l2cap_chan_hold_unless_zero() returns NULL, the code jumps to shutdown_already without a matching sock_put(), leaking the reference on every such invocation.
```
