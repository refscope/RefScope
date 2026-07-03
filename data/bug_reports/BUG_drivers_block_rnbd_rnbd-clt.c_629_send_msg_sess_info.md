# REAL BUG: drivers/block/rnbd/rnbd-clt.c:629 send_msg_sess_info()

**Confidence**: HIGH | **Counter**: `$->busy.counter`

## Reasoning

| 615→if(err) branch | error (send_usr_msg fail)  | YES | YES (put at L618) + YES (put at L623) | ❌ EXCESS | Double put on send failure |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 591   | error (rsp alloc fail)      | NO (before get) | N/A | ✅ | rnbd_get_iu not called |
| 596   | error (iu get fail)         | NO (get returned NULL) | N/A | ✅ | rnbd_get_iu failed, no ref |
| 607→goto put_iu | goto put_iu on sess get fail | YES (rnbd_get_iu succeeded) | YES (first put at label L618) + YES (second put at L623) | ❌ EXCESS | Double put; falls through to L623 after label |
| 615→if(err) branch | error (send_usr_msg fail)  | YES | YES (put at L618) + YES (put at L623) | ❌ EXCESS | Double put on send failure |
| 620 (else) → L623 | success                     | YES | YES (only L623) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
send_msg_sess_info() double-calls rnbd_put_iu() on all error paths via the misplaced `put_iu` label and the unconditional trailing put, causing a refcount excess put on the iu's counter.
```
