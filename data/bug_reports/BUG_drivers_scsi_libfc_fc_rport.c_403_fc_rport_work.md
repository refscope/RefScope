# REAL BUG: drivers/scsi/libfc/fc_rport.c:403 fc_rport_work()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

| L401→403 (default) | break→final put | NO | L403 only | YES | single event put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L295 | return (READY early fail) | YES (L284) | YES (L294) | NO (leak) | work ref not released |
| L321→403 | break→final put | YES (L284) | YES (L320, L403) | YES | 1 get + 2 puts → net -1 |
| L403 (FAILED: cancel true, DELETE+DIR_SERV) | break→final put | NO | L347, L369, L403 | ❌ EXCESS | expected 2 puts (event+retry), got 3 |
| L403 (FAILED: cancel true, DELETE+retry condition) | break→final put | NO | L347, L403 | YES | retry+event refs released |
| L403 (FAILED: cancel true, DELETE+else) | break→final put | NO | L347, L384, L403 | ❌ EXCESS | extra event put |
| L403 (FAILED: cancel true, rp_state != DELETE) | break→final put | NO | L347, L403 | YES | retry+event refs released |
| L403 (FAILED: cancel false, DELETE+DIR_SERV) | break→final put | NO | L369, L403 | ❌ EXCESS | double event_put |
| L403 (FAILED: cancel false, DELETE+retry condition) | break→final put | NO | L403 only | YES | single event put |
| L403 (FAILED: cancel false, DELETE+else) | break→final put | NO | L384, L403 | ❌ EXCESS | double event_put |
| L403 (FAILED: cancel false, rp_state != DELETE) | break→final put | NO | L403 only | YES | single event put |
| L401→403 (default) | break→final put | NO | L403 only | YES | single event put |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The final kref_put at L403 is unconditional, but paths in the FAILED/LOGO/STOP case that already release the event_work reference (L369, L384) end up double-putting it, causing a refcount underflow and the reported excess put warning.
```
