# REAL BUG: drivers/md/dm-crypt.c:2164 kcryptd_crypt_read_convert()

**Confidence**: MEDIUM | **Counter**: `$->io_pending.counter`

## Reasoning

fter it causes a double‑decrement (underflow). Without the callee source that is uncertain. |

[NEED_SOURCE] kcryptd_crypt_read_done  
[NEED_SOURCE] crypt_dec_pending  
[NEED_SOURCE] crypt_inc_pending

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2147 (early return) | r == BLK_STS_DEV_RESOURCE → return | YES (crypt_inc_pending at L2134) | NO (transferred to work, work likely will put) | ✅ Transfer | Work `kcryptd_crypt_read_continue` will later crypt_dec_pending. |
| L2164 (fall‑through) | normal return | YES (crypt_inc_pending at L2134) | YES (crypt_dec_pending at L2164) | ❓ Potentially excess if kcryptd_crypt_read_done() already calls crypt_dec_pending() | The refcount audit marks the crypt_dec_pending at L2164 as **excess put**. That strongly suggests that `kcryptd_crypt_read_done()` internally already decrements `io->io_pending`, so the explicit `crypt_dec_pending` after it causes a double‑decrement (underflow). Without the callee source that is uncertain. |

[NEED_SOURCE] kcryptd_crypt_read_done  
[NEED_SOURCE] crypt_dec_pending  
[NEED_SOURCE] crypt_inc_pending  

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM

The pattern strongly suggests that `kcryptd_crypt_read_done()` already includes a final `crypt_dec_pending` (or equivalent put) on `io->io_pending`. The explicit `crypt_dec_pending` at line 2164 after the `done()` call is therefore an **extra decrement**, triggering the excess put warning. If this interpretation holds the fall‑through path has GET=YES and PUT=YES (explicit) but the PUT is redundant, making it an underflow. The early‑return workqueue path is balanced by transfer, so the bug is on the normal path.
```
