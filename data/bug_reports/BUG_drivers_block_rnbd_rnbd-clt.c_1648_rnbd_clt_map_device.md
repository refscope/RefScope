# REAL BUG: drivers/block/rnbd/rnbd-clt.c:1648 rnbd_clt_map_device()

**Confidence**: HIGH | **Counter**: `$->busy.counter`

## Reasoning

| ~L1610 | `return dev` (success) | YES | YES (once) | ✅ | |

## Full Response

```
| Line | Return Type | GET (iu)? | PUT (iu)? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L1539 | `return ERR_PTR(-EEXIST)` | NO | N/A | ✅ | |
| ~L1542 | `return ERR_CAST(sess)` after `IS_ERR(sess)` | NO | N/A | ✅ | |
| ~L1548 | `goto put_sess` → `return ERR_PTR(ret)` | NO | N/A | ✅ | |
| ~L1553 | `goto put_dev` → `return ERR_PTR(ret)` | NO | N/A | ✅ | |
| ~L1558 | `goto del_dev` → `return ERR_PTR(ret)` | NO | N/A | ✅ | |
| ~L1564 | `kfree(rsp); goto del_dev` → `return ERR_PTR(ret)` | NO | N/A | ✅ | `rnbd_get_iu()` failed, no iu held |
| ~L1576 (send_usr_msg **fails**) | first `if (ret)` block calls `rnbd_put_iu(sess, iu);` then `if (ret)` → `goto put_iu` → `rnbd_put_iu(sess, iu);` again | YES (one get) | **YES (twice)** | ❌ **EXCESS PUT** | Double put on iu |
| ~L1576 (send_usr_msg succeeds, `errno != 0`) | `goto put_iu` (single `rnbd_put_iu`) | YES | YES (once) | ✅ | |
| ~L1610 | `return dev` (success) | YES | YES (once) | ✅ | |

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  

In the error path of `send_msg_close` (when `ret != 0`), `rnbd_put_iu(sess, iu)` is called explicitly inside the first `if (ret)` block, but the code then falls through to `if (ret)` again and `goto put_iu`, which calls `rnbd_put_iu` a second time. This causes an excess put on the busy counter (refcount underflow).
```
