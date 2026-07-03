# REAL BUG: drivers/net/ethernet/cavium/liquidio/lio_core.c:1826 liquidio_get_fec()

**Confidence**: HIGH | **Counter**: `$->sc_buf_pool.alloc_buf_count.counter`

## Reasoning

- `WRITE_ONCE(sc->caller_is_done, true)` does not trigger a free; it is a flag used by an async completion handler, but the function itself abandons the allocated `sc` on both non‑error paths.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L1776 | error (-ENOMEM) | NO (sc == NULL) | N/A | ✅ | allocation failed, no ref held |
| ~L1802 | error (-EIO) | YES (sc allocated) | YES (octeon_free_soft_command) | ✅ | send fails, sc freed |
| ~L1805 | error (retval != 0 after wait) | YES | NO | ❌ LEAK | wait_timeout error, sc not freed |
| ~L1826 | success (retval == 0) | YES | NO | ❌ LEAK | function succeeds, sc never freed (only sets caller_is_done) |

Details:
- octeon_alloc_soft_command() acquires a soft command (and its buffer pool refcount).  
- IQ_SEND_FAILED path explicitly calls octeon_free_soft_command() – correct.  
- The `if (retval)` return from `wait_for_sc_completion_timeout` returns without freeing `sc` → leak.  
- The final `return retval;` after processing also does not free `sc` → leak.  
- `WRITE_ONCE(sc->caller_is_done, true)` does not trigger a free; it is a flag used by an async completion handler, but the function itself abandons the allocated `sc` on both non‑error paths.  

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Missing octeon_free_soft_command(oct, sc) on the wait‑timeout error path and the normal success path causes an imbalance in sc_buf_pool.alloc_buf_count.
```
