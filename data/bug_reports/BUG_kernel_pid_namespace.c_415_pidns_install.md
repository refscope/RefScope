# REAL BUG: kernel/pid_namespace.c:415 pidns_install()

**Confidence**: MEDIUM | **Counter**: `$->ns.__ns_ref.refs.counter`

## Reasoning

d then gets the new one. If the new namespace equals the old one, the put will release the last reference, freeing the namespace, and the subsequent get on the same, now-freed pointer is a use-after-free that manifests as a refcount excess put. The error paths do not trigger any get/put imbalance.

## Full Response

```
| Line | Return Type | GET Done? (get_pid_ns(new)) | PUT Done? (put_pid_ns(old)) | Balanced? | Notes |
|------|-------------|----------------------------|----------------------------|-----------|-------|
| L400 | -EPERM      | NO (before get)            | N/A                        | ✅         | No get, no put on new. |
| L409 | -EINVAL     | NO (before get)            | N/A                        | ✅         | No get, no put. |
| L413 | 0 (success) | YES                        | YES (on old nsproxy->pid_ns_for_children) | ⚠️ UAF/Excess Put if old==new | If the same pid namespace is already stored in pid_ns_for_children, `put_pid_ns(old)` drops its refcount to 0 (frees the namespace), then `get_pid_ns(new)` operates on freed memory and causes an "excess put" pattern (refcount going to zero unexpectedly). No check for old == new. |

**Reasoning**: On success, pidns_install unconditionally puts the old pid_ns_for_children and then gets the new one. If the new namespace equals the old one, the put will release the last reference, freeing the namespace, and the subsequent get on the same, now-freed pointer is a use-after-free that manifests as a refcount excess put. The error paths do not trigger any get/put imbalance.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM
```
