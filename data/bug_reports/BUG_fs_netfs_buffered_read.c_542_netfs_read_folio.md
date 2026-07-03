# REAL BUG: fs/netfs/buffered_read.c:542 netfs_read_folio()

**Confidence**: MEDIUM | **Counter**: `$->ref.refs.counter`

## Reasoning

Pending confirmation, the warning pattern matches a known class of bugs where an error‑handling function releases a resource that the caller also attempts to release.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L504 (folio_test_dirty) | return netfs_read_gaps | NO (before alloc) | N/A | ✅ | never alloc |
| L515 (IS_ERR(rreq)) | goto alloc_error → return | NO (alloc failed) | N/A | ✅ | ERR_PTR → no ref |
| L522 (ret == -ENOMEM/… ) | goto discard → return | YES (alloc succeeded) | YES (netfs_put_failed_request) | ❌ Double-put if callee already put | Warning at L542 – possible extra put from `netfs_begin_cache_read` |
| L529 (ret < 0) | goto discard → return | YES | YES | ❌ Double-put if callee already put | Same, via `netfs_create_singular_buffer` |
| L533–536 (success) | return 0/ret | YES | YES (netfs_put_request) | ✅ | normal put on success |

**Note:** The static checker warning “refcount excess put” on line 542 (`netfs_put_failed_request`) implies that by the time the `discard` label is reached, the request’s refcount has already been decremented once, making the explicit put here an excess. The only way this occurs is if `netfs_begin_cache_read` or `netfs_create_singular_buffer` internally calls `netfs_put_request` (or equivalent) on failure before returning. This would create a double-put on the error paths that jump to `discard`.

To confirm, we need the source of:
[NEED_SOURCE] netfs_begin_cache_read
[NEED_SOURCE] netfs_create_singular_buffer
[NEED_SOURCE] netfs_put_failed_request

Pending confirmation, the warning pattern matches a known class of bugs where an error‑handling function releases a resource that the caller also attempts to release.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
```
