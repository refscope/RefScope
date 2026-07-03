# REAL BUG: fs/smb/smbdirect/connection.c:1264 smbdirect_connection_send_single_iter()

**Confidence**: HIGH | **Counter**: `sc->send_io.credits.count.counter`

## Reasoning

| L153 | return data_length                  | YES (credit used for send) | NO | ✅ | credit correctly consumed, not returned |

## Full Response

```
| Line | Return Type | Send Credit Consumed? | atomic_inc (credit return) Done? | Balanced? | Notes |
|------|-------------|------------------------|---------------------------------|-----------|-------|
| L17  | return -EINVAL                      | NO (before any credit acquisition) | N/A | ✅ | early validation |
| L21  | return -EINVAL                      | NO | N/A | ✅ | iter check |
| L26  | return -EINVAL                      | NO | N/A | ✅ | remaining_data_length check |
| L31  | return -EINVAL                      | NO | N/A | ✅ | no-payload check |
| L40  | return -ENOTCONN                    | NO | N/A | ✅ | not connected |
| L50  | goto bcredit_failed (wait bcredit fail) | NO (wait_for_send_credits not reached) | NO | ✅ | bcredit_failed does not inc credits.count |
| L54  | goto lcredit_failed (wait lcredit fail) | NO | NO | ✅ | lcredit_failed does not inc credits.count |
| L58  | goto credit_failed (wait send credit fail) | NO (wait_for_send_credits returned error) | NO | ✅ | credit_failed does not inc credits.count, no credit consumed |
| L82  | goto credit_failed (wait_event fail) | YES (wait_for_send_credits succeeded, credit taken) | NO (credit_failed skips alloc_failed) | ❌ LEAK | Missing atomic_inc to return the send credit → later excess put |
| L90  | goto alloc_failed (alloc msg fail)  | YES | YES (alloc_failed does atomic_inc) | ✅ | credit returned |
| L99  | goto err (dma map error)            | YES | YES (err → flush_failed → alloc_failed) | ✅ | credit returned on failure |
| L112 | goto err (sg map error)             | YES | YES | ✅ | credit returned |
| L140 | goto err (post send fail)           | YES | YES | ✅ | credit returned |
| L150 | goto flush_failed (flush fail)      | YES (credit used for send) | YES (falls through to alloc_failed, incs erroneously) | ❌ EXCESS GET | credit should not be returned after the send was posted; imbalance in opposite direction |
| L153 | return data_length                  | YES (credit used for send) | NO | ✅ | credit correctly consumed, not returned |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Missing atomic_inc(&sc->send_io.credits.count) on the L82 goto credit_failed path after wait_for_send_credits succeeded but wait_event failed; this causes a send credit to be taken but never returned, eventually leading to an underflow (excess put) in cleanup.
```
