# REAL BUG: drivers/scsi/qla2xxx/qla_os.c:5494 qla2x00_do_work()

**Confidence**: MEDIUM | **Counter**: `e->u.iosb.sp->cmd_kref.refcount.refs.counter`

## Reasoning

| Loop exit (EAGAIN break or list exhausted) | function return | N/A | N/A | N/A | sp not directly released after loop, but multiple puts already performed |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L5512 (case QLA_EVT_UNMAP) | falls through; continues loop or breaks | NO (no get in this function) | YES (qla24xx_sp_unmap unconditionally puts sp->cmd_kref) | ❌ **excess put possible** if another event on the same sp also puts | |
| L5530 (case QLA_EVT_SCAN_CMD) | falls through; continues loop or breaks | NO | YES (conditional, via qla_fab_async_scan → kref_put) | ❌ **excess put possible** if another event on the same sp also puts and this condition does put | |
| L5533 (case QLA_EVT_SP_RETRY) | falls through; continues loop or breaks | unknown (qla_sp_retry contract unclear) | unknown (qla_sp_retry may put) | ❌ **potential double-put** if it puts and any other put on the same sp exists | |
| Loop exit (EAGAIN break or list exhausted) | function return | N/A | N/A | N/A | sp not directly released after loop, but multiple puts already performed |

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
Multiple work‑event handlers (QLA_EVT_UNMAP, QLA_EVT_SCAN_CMD, and possibly QLA_EVT_SP_RETRY) can put the same `sp->cmd_kref` without any inter‑event reference counting guard. If two such events are queued for the same `sp`, the second handler will perform an excess `kref_put`, matching the warning.
```
