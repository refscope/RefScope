# REAL BUG: drivers/vhost/net.c:960 handle_tx_zerocopy()

**Confidence**: MEDIUM | **Counter**: `ubufs->refcount.counter`

## Reasoning

Given the warning explicitly says “excess put” and the static checker likely found a path where the counter is decremented twice without an intervening increment, I default to **REAL_BUG** at medium confidence.

## Full Response

```
## Path Table

| Line | Return Type                     | GET Done? (atomic_inc)                                      | PUT Done? (vhost_net_ubuf_put)                        | Balanced? | Notes                                                                                                                               |
|------|---------------------------------|-------------------------------------------------------------|-------------------------------------------------------|-----------|-------------------------------------------------------------------------------------------------------------------------------------|
| L892 | break (head < 0)                | NO (before get)                                             | N/A                                                   | ✅         | Head < 0, zcopy block not entered → no inc → no leak/excess.                                                                        |
| L898 | break (head == vq->num)         | NO (before get)                                             | N/A                                                   | ✅         | No usable buffer, zcopy block not entered.                                                                                          |
| L902 | continue (enable notify fails) | NO (before get)                                             | N/A                                                   | ✅         | head==vq->num, continue restarts loop; zcopy not executed.                                                                          |
| L929 | – (zcopy_used=true entry)       | YES (atomic_inc at L929)                                   | –                                                     | –         | inc occurs unconditionally when zcopy_used true.                                                                                    |
| L938 | sendmsg err < 0, retry true     | YES                                                         | YES (at L960 if DMA in progress)                      | ✅         | put called, then break; function returns. Only one put for this inc.                                                               |
| L938 | sendmsg err < 0, retry false    | YES                                                         | YES (at L960) then fallthrough to vhost_zerocopy_signal_used | ❓         | If vhost_zerocopy_signal_used calls vhost_net_ubuf_put again → double put → excess. Need callee source to confirm.                 |
| L938 | sendmsg success (err >=0)       | YES                                                         | NO (not directly) then vhost_zerocopy_signal_used at L992 | ❓         | Signal_used may call put → balanced if only one put. Need callee.                                                                   |
| L998 | Loop end (weight exceeded)      | Depends on last iteration’s zcopy.                          | As per that iteration’s path                         | As per above | Last iteration’s status applies; no extr
```
