# REAL BUG: net/ipv4/tcp.c:1443 tcp_sendmsg_locked()

**Confidence**: LOW | **Counter**: `uarg->refcnt.refs.counter`

## Reasoning

, all data) | **YES (if any skb received ≥2 calls)** | Only net_zcopy_put (initial ref)       | ❌ **LEAK** | If any skb got multiple skb_zerocopy_iter_stream calls, the extra refcount is never released                                                                                              |

## Full Response

```
| Line     | Return Type                 | GET Done? (skb_zerocopy_iter_stream) | PUT Done? (matching release)           | Balanced? | Notes                                                                                                                                                                                      |
|----------|-----------------------------|--------------------------------------|----------------------------------------|-----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| L1152    | goto out_err (realloc fail) | NO (call never reached)              | N/A (uarg == NULL)                     | ✅         |                                                                                                                                                                                            |
| L1164    | goto out_err (binding err)  | NO (before stream call)              | YES (net_zcopy_put_abort releases uarg) | ✅         |                                                                                                                                                                                            |
| L1186    | goto out_err (fastopen err) | NO (before stream call)              | YES (net_zcopy_put_abort)              | ✅         |                                                                                                                                                                                            |
| ~L1410   | continue loop (first success) | YES (first call)                    | No explicit put; ref held by skb       | ✅         | skb destructor will later release this ref                                                                                                                                                  |
| **~L1443** | **goto new_segment (E -EMSGSIZE/-EEXIST)** | **YES (unconditional get)** | No put; skb pushed, ref transferred | ✅         | skb pushed; its ref will be released on completion                                                                                                                                        |
| **~L1443** | **goto do_error after err<0 (copied==0)** | **YES**                            | YES (tcp_remove_empty_skb + put_abort) | ✅         | empty skb freed releasing ref, put_abort cleans rest                                                                                                                                       |
| **~L1443** | **goto do_error after err<0 (copied>0)** | **YES**                            | No extra put; skb still has ref        | ✅ (for this error) | skb lives, ref will be released later; only initial ref is released via net_zcopy_put                                                                                                      |
| **~L1443** | **second successful call o
```
