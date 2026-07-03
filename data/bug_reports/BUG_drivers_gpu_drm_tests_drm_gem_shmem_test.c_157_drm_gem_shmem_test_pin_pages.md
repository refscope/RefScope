# REAL BUG: drivers/gpu/drm/tests/drm_gem_shmem_test.c:157 drm_gem_shmem_test_pin_pages()

**Confidence**: HIGH | **Counter**: `$->pages_pin_count.refs.counter`

## Reasoning

rmal return | YES | YES (explicit unpin) | ❌ **EXCESS PUT** | Cleanup action registered at L142 executes after function returns → calls `drm_gem_shmem_free_wrapper` → `drm_gem_object_put` → `drm_gem_shmem_free_object` → `drm_gem_shmem_unpin` again, decrementing the already-zero `pages_pin_count` |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L137 (KUNIT_ASSERT fails) | error abort | NO (before get) | N/A | ✅ | shmem create failed |
| L143 (KUNIT_ASSERT fails after kunit_add_action_or_reset) | error abort | NO | N/A | ✅ | no get yet |
| L146 (KUNIT_ASSERT fails after drm_gem_shmem_pin returned error) | error abort | NO (conditional get failed) | N/A | ✅ | pin returned error, ref not taken |
| L147 (KUNIT_ASSERT fails after successful pin) | error abort | YES | NO (explicit put skipped) | ✅ (balanced by cleanup) | cleanup action runs on abort → `drm_gem_object_put` → `drm_gem_shmem_free_object` → `drm_gem_shmem_unpin` |
| L150/151 (KUNIT_ASSERT fails in page loop) | error abort | YES | NO | ✅ (balanced by cleanup) | same as above |
| L153 (unpin) → normal return via end of function | normal return | YES | YES (explicit unpin) | ❌ **EXCESS PUT** | Cleanup action registered at L142 executes after function returns → calls `drm_gem_shmem_free_wrapper` → `drm_gem_object_put` → `drm_gem_shmem_free_object` → `drm_gem_shmem_unpin` again, decrementing the already-zero `pages_pin_count` |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The test explicitly calls `drm_gem_shmem_unpin()` at L153, reducing the pin refcount to 0. After the function returns, the cleanup action registered via `kunit_add_action_or_reset` calls `drm_gem_shmem_free_wrapper`, which triggers `drm_gem_shmem_free_object` → `drm_gem_shmem_unpin` again, causing an excess decrement on `pages_pin_count`.
```
