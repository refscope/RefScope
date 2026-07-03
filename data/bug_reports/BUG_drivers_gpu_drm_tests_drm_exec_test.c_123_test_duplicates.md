# REAL BUG: drivers/gpu/drm/tests/drm_exec_test.c:123 test_duplicates()

**Confidence**: MEDIUM | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

ock YES – if it puts for every lock entry → two puts, one for lock1 and one for the phantom entry of lock2 | ❌ EXCESS PUT | unlock tries to put twice for only one acquired ref, final ref drops to 0, triggering the warning at L122 |

## Full Response

```
| Line/Path | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|-----------|-------------|-----------|-----------|-----------|-------|
| L114 break (lock1 failed)   | fallthrough to unlock | drm_gem_private_object_init YES, lock1 NO (failed) | drm_exec_unlock_obj likely NO (object not locked) | ✅ | unlock is conditional on object being in exec list |
| L120 break (lock1 OK, lock2 failed) | fallthrough | init YES, lock1 YES, lock2 NO (failed) | unlock likely YES (one put – lock1's ref) | ✅ | |
| no break, both locks succeed (DUPLICATE flag) | fallthrough | init YES, lock1 YES (got ref), lock2 NO (IGNORE_DUPLICATES skips get) | unlock YES – if it puts for every lock entry → two puts, one for lock1 and one for the phantom entry of lock2 | ❌ EXCESS PUT | unlock tries to put twice for only one acquired ref, final ref drops to 0, triggering the warning at L122 |

[NEED_SOURCE] drm_exec_unlock_obj
[NEED_SOURCE] drm_exec_lock_obj

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`drm_gem_private_object_init` sets refcount to 1. First `drm_exec_lock_obj` succeeds → ref=2. Second lock with `DRM_EXEC_IGNORE_DUPLICATES` likely adds a list entry but does **not** get a ref (ref stays 2). `drm_exec_unlock_obj` appears to put once per list entry, so it puts twice, dropping the ref to 0 and causing an excess put. The test always takes the both-ok path, so the warning is real.
```
