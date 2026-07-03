# REAL BUG: drivers/scsi/libfc/fc_exch.c:1656 fc_exch_recv_seq_resp()

**Confidence**: HIGH | **Counter**: `$->ex_refcnt.counter`

## Reasoning

| L1625 (goto skip_resp) | rc != 0 | YES | YES (fc_exch_release at skip_resp) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1579 (goto out) | ep NULL | NO (fc_exch_find returned NULL) | N/A | ✅ | no reference taken |
| L1581 (goto rel) | ESB_ST_COMPLETE set | YES (fc_exch_find succeeded) | YES (fc_exch_release at rel) | ✅ | |
| L1586 (goto rel) | sid mismatch | YES | YES | ✅ | |
| L1593 (goto rel) | did mismatch | YES | YES | ✅ | |
| L1622 (rc == 0 → fc_exch_delete, then fall through) | completion, delete | YES (from find) | YES (fc_exch_delete likely does final put) AND YES (fc_exch_release at skip_resp) | ❌ EXCESS PUT | double release: delete then release |
| L1625 (goto skip_resp) | rc != 0 | YES | YES (fc_exch_release at skip_resp) | ✅ | |
| L1630 (condition false, normal flow) | normal | YES | YES (fc_exch_release at skip_resp) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
When `fc_exch_done_locked` returns 0, `fc_exch_delete` is called (which does a final put), but execution then falls through to `skip_resp` where `fc_exch_release` does another put, causing an excess put.
```
