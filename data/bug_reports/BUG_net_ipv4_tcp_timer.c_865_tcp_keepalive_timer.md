# REAL BUG: net/ipv4/tcp_timer.c:865 tcp_keepalive_timer()

**Confidence**: HIGH | **Counter**: `$->sk_refcnt.refs.counter`

## Reasoning

| L850       | fallthrough to resched → out (wakeup ok)   | YES (tcp_reset_keepalive_timer) | YES (callback sock_put) | ✅ | Timer re-armed, reference released |

## Full Response

```
| Line       | Return Type         | GET Done? (tcp_reset_keepalive_timer) | PUT Done? (sock_put from tcp_done + callback) | Balanced? | Notes                                                                                                                                                  |
|------------|---------------------|---------------------------------------|-----------------------------------------------|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| L789       | goto out (sock owned) | YES (tcp_reset_keepalive_timer)       | YES (callback sock_put at out)                | ✅        | Keepalive re-armed, reference released by callback's put                                                                                                |
| L793       | goto out (LISTEN)   | NO                                    | YES (callback sock_put)                        | ⚠️        | No get, but callback put releases timer reference; balanced if timer reference exists. (Normal callback pattern)                                         |
| L798‑L803  | goto out (FIN_WAIT2 linger timeout) | NO (tcp_time_wait does not get)       | YES (callback sock_put)                        | ⚠️        | tcp_time_wait releases socket; callback put may be redundant if tcp_time_wait already put, but not necessarily excess (tricky). Not related to death. |
| L805‑L806  | goto death (FIN_WAIT2 active reset) | NO                    | YES (tcp_done does sock_put) + YES (callback sock_put at out) | ❌ EXCESS | tcp_done calls sock_put, then falls through to out → second sock_put → refcount underflow                                                                   |
| L810       | goto out (not KEEPOPEN or CLOSE) | NO                       | YES (callback sock_put)                        | ⚠️        | Standard path, release callback reference                                                                                                                |
| L817       | goto resched → out  | YES (tcp_reset_keepalive_timer)       | YES (callback sock_put)                        | ✅        | Timer re-armed, reference released                                                                                                                     |
| L834‑L838  | goto out (keepalive timeout)       | NO                    | YES (callback sock_put)                        | ⚠️        | Normal path, release callback reference                                                                                                                |
| L845‑L847  | fallthrough to resched → out (wakeup failed) | YES (tcp_reset_keepalive_timer) | YES (callback sock_put) | ✅ | Timer re-armed, reference released |
| L850       | fallthrough to resched → out (wakeup ok)   | YES (tcp_reset_keepalive_timer) | YES (callback sock_put) | ✅ | Timer re-armed, reference released |

**VERDICT: REAL_BUG**
```
