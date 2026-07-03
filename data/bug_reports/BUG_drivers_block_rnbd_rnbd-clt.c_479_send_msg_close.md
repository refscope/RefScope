# REAL BUG: drivers/block/rnbd/rnbd-clt.c:479 send_msg_close()

**Confidence**: HIGH | **Counter**: `$->busy.counter`

## Reasoning

| L480 (err==0 path) | success | YES | YES (L479 once) | ✅ (iu) | dev get leaked (no put_dev here), but iu balanced |

## Full Response

```
```
| Line | Return Type | GET Done? (iu) | PUT Done? (iu) | Balanced? | Notes |
|------|---------------|----------------|----------------|-----------|-------|
| L461 | error (-ENOMEM) | NO (iu == NULL) | N/A | ✅ | get failed, no put needed |
| L480 (err≠0 path) | error (via if block) | YES | YES x2 (L474 and L479) | ❌ **EXCESS PUT** | `rnbd_put_iu` called twice, second at L479 is an extra put on `busy.counter` |
| L480 (err==0 path) | success | YES | YES (L479 once) | ✅ (iu) | dev get leaked (no put_dev here), but iu balanced |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
In `send_msg_close()`, on the `send_usr_msg` error path (L472 `if (err)`), `rnbd_put_iu(sess, iu)` is called at L474 inside the block and again unconditionally at L479, causing a double put on the `iu` reference — an excess put on `$->busy.counter`.
```
```
