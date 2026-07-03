# REAL BUG: net/core/dev.c:6191 __netif_receive_skb_core()

**Confidence**: HIGH | **Counter**: `$->users.refs.counter`

## Reasoning

rev) *ppt_prev = pt_prev` transfers ownership to caller; otherwise skb is dropped.                                                                                                                     |

## Full Response

```
| Line   | Return Type             | GET Done?                                                         | PUT Done?                          | Balanced? | Notes                                                                                                                                                                                                                           |
|--------|--------------------------|-------------------------------------------------------------------|------------------------------------|-----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ~6012  | goto out (XDP drop)      | NO (before any GET)                                               | N/A                                | ✅         | No ref acquired.                                                                                                                                                                                                                  |
| ~6021  | goto out (vlan_untag NULL)| NO (before GET)                                                   | N/A                                | ✅         | skb becomes NULL.                                                                                                                                                                                                                 |
| ~6048  | goto another_round       | YES (sch_handle_ingress)                                          | N/A (loop continues)               | ✅         | Reference is held across another_round; the skb will eventually be processed and resolved (drop or passed to caller).                                                                                                          |
| ~6049  | goto out (!skb)          | YES (sch_handle_ingress returned NULL, so no skb)                 | N/A                                | ✅         | No skb → no ref to put.                                                                                                                                                                                                          |
| ~6052  | goto out (nf_ingress fail)| YES (sch_handle_ingress unconditional GET, and possibly deliver_skb from previous loops) | NO (skips both the `*ppt_prev` assignment and the `drop` path) | ❌ **LEAK** | `sch_handle_ingress` is an unconditional GET that always increments the refcount. The `goto out` bypasses any matching PUT (`kfree_skb_reason` or the handler delivery). The skb’s refcount remains elevated on return. |
| ~6087  | goto out (rx_handler CONSUMED) | YES (deliver_skb may have been called)                        | N/A – handler consumed the skb     | ✅         | The handler has taken ownership and will release the ref.                                                                  
```
