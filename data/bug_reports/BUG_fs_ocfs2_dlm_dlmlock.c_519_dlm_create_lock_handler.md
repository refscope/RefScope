# REAL BUG: fs/ocfs2/dlm/dlmlock.c:519 dlm_create_lock_handler()

**Confidence**: MEDIUM | **Counter**: `$->lock_refs.refcount.refs.counter`

## Reasoning

s: NO | ⚠️  On error: if dlmlock_master internally releases its get on error → caller PUT becomes excess → **REAL_BUG**. If dlmlock_master does NOT release internally → caller PUT insufficient (leak), but warning is “excess” so unlikely. | Warning indicates smatch sees an extra put on this path. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L449 (dlm_grab fail) | DLM_REJECTED | N/A | N/A | ✅ | No lock allocated |
| L456 (goto leave, domain not joined) | DLM_REJECTED | N/A | N/A | ✅ | newlock NULL |
| L462 (goto leave, namelen too long) | DLM_IVBUFLEN | N/A | N/A | ✅ | newlock NULL |
| L469 (goto leave, dlm_new_lock fail) | DLM_SYSERR | N/A | N/A | ✅ | newlock NULL |
| L476 (goto leave, dlm_lookup_lockres fail) | DLM_IVLOCKID | NO (dlmlock_master not called) | YES (newlock non-null, status != NORMAL) | ✅ | Only initial ref, put correct |
| L484 (goto leave, lockres state not NORMAL) | status ≠ DLM_NORMAL | NO | YES | ✅ | As above, dlmlock_master not called |
| L492 (dlmlock_master call, then leave) | status from dlmlock_master | YES (unconditional get inside dlmlock_master) | If error: YES (caller put). If success: NO | ⚠️  On error: if dlmlock_master internally releases its get on error → caller PUT becomes excess → **REAL_BUG**. If dlmlock_master does NOT release internally → caller PUT insufficient (leak), but warning is “excess” so unlikely. | Warning indicates smatch sees an extra put on this path. |

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`dlmlock_master` gets an unconditional lock reference (`dlm_lock_get`). On error, the caller unconditionally calls `dlm_lock_put(newlock)` at the `leave` label. If `dlmlock_master` internally releases its own get on error (common pattern), this results in a double-put / refcount underflow matching the `excess put` warning. Without `dlmlock_master` source this cannot be fully confirmed, but smatch’s tracking of an extra put strongly points to a real bug. Request `dlmlock_master` source to verify the error-unwind logic.
```
