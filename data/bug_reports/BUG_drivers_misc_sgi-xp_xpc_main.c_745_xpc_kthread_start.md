# REAL BUG: drivers/misc/sgi-xp/xpc_main.c:745 xpc_kthread_start()

**Confidence**: MEDIUM | **Counter**: `$->references.counter`

## Reasoning

L745 corresponds to `xpc_part_deref(part)`. On the path where the `DISCONNECTING` flag is set, `waitmsgs` is skipped → GET does not happen, but the final `xpc_part_deref` is still called → excess put.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L690..L745 (waitmsgs called) | L745 return | YES (xpc_kthread_waitmsgs is a GET tracked by smatch) | YES (xpc_msgqueue_deref + xpc_part_deref) | ✅ Balanced | Both gets and puts occur |
| L670..L745 (skip waitmsgs, DISCONNECTING set) | L745 return | NO (waitmsgs not called) | YES (same puts) | ❌ EXCESS PUT | `xpc_part_deref` (or `xpc_msgqueue_deref`) called without matching get |

**Note**: smatch tracked `xpc_kthread_waitmsgs` as a GET operation on `$->references.counter`. The warning line L745 corresponds to `xpc_part_deref(part)`. On the path where the `DISCONNECTING` flag is set, `waitmsgs` is skipped → GET does not happen, but the final `xpc_part_deref` is still called → excess put.

[NEED_SOURCE] xpc_kthread_waitmsgs
[NEED_SOURCE] xpc_part_deref
[NEED_SOURCE] xpc_msgqueue_deref

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
xpc_kthread_start always calls xpc_part_deref/xpc_msgqueue_deref, but skips xpc_kthread_waitmsgs (a refcount get) when the channel is disconnecting, causing an excess put on the partition reference count.
```
