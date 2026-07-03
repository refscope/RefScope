# REAL BUG: fs/ocfs2/dlm/dlmlock.c:741 dlmlock()

**Confidence**: HIGH | **Counter**: `$->lock_refs.refcount.refs.counter`

## Reasoning

, eventually non-DLM_NORMAL goto error | error | NO (assumed, conditional fails) | YES (1 put, initial) | ✅ | remote didn’t inc on retry fails, balanced |

## Full Response

```
```
| Line         | Return Type         | GET Done? | PUT Done? | Balanced? | Notes |
|--------------|---------------------|-----------|-----------|-----------|-------|
| L550         | early return BADARGS| NO        | N/A       | ✅ | no lock |
| L556 (goto error) | error              | NO        | N/A       | ✅ | no lock |
| L561 (goto error) | error              | NO        | N/A       | ✅ | no lock |
| L568 (goto error) | error              | NO        | N/A       | ✅ | no lock |
| L573 (goto error) | error              | NO        | N/A       | ✅ | no lock, convert flag but before convert block |
| convert: lock==NULL goto error  | error              | NO        | N/A       | ✅ | no lock ref |
| convert: res==NULL goto error   | error              | NO        | N/A       | ✅ | no lock ref, no res ref taken |
| convert: args mismatch goto error | error              | NO        | N/A       | ✅ | res_get done, res_put at error label, lock not affected |
| convert: DLM_NORMAL fallthrough to error label    | success             | NO (no master/remote) | NO | ✅ | no lock ref changes |
| convert: non-DLM_NORMAL fallthrough to error label| error               | NO (no master/remote) | NO | ✅ | no lock ref changes |
| lock creation: lock==NULL goto error | error              | NO        | N/A       | ✅ | no lock |
| lock path: res==NULL goto error after dlm_new_lock | error              | NO (before master/remote) | YES (1 put, initial ref) | ✅ | initial ref released |
| after dlmlock_master call: status != DLM_NORMAL (non-retry) goto error | error | YES (unconditional dlm_lock_get) | YES (1 put, initial) | ❌ LEAK | master added ref, only initial ref put, extra ref remains |
| after dlmlock_master call: retry status loop, eventually non-DLM_NORMAL goto error | error | YES (multiple gets due to retries) | YES (1 put, initial) | ❌ LEAK | multiple extra refs, only one put, refcount inflated |
| after dlmlock_master: status == DLM_NORMAL (success) | success | YES (unconditional) | NO | ✅ (by design) | lock holds extra ref for lifetime |
| after dlmlock_remote: status != DLM_NORMAL (non-retry) goto error | error | NO (conditional, failed) | YES (1 put, initial) | ✅ | remote did not inc ref on failure, initial freed |
| after dlmlock_remote: retry loop, eventually non-DLM_NORMAL goto error | error | NO (assumed, conditional fails) | YES (1 put, initial) | ✅ | remote didn’t inc on retry fails, balanced |
| after dlmlock_remote: status == DLM_NORMAL (success) | success | YES (conditional) | NO | ✅ (by design) | remote inc ref, held for lifetime |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
dlmlock_master unconditionally increments the lock refcount, but error paths after its call release only the initial reference via dlm_lock_put once, leaking the extra reference; retry loops aggravate the leak.
```
```
