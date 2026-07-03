# REAL BUG: fs/afs/server.c:282 afs_lookup_server()

**Confidence**: HIGH | **Counter**: `$->ref.refs.counter`

## Reasoning

| L282 out (any path, candidate NULL) | success/error | NO (candidate NULL) | N/A | ✅ | candidate consumed by install or already NULL. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L198 (early return server) | success | NO (no alloc) | N/A | ✅ | Server found, no candidate allocation. |
| ~L207 (candidate NULL) | error (-ENOMEM) | NO (candidate NULL) | N/A | ✅ | Allocation failed, no ref held. |
| L282 out (wait_for_creation, candidate non‑NULL) | success/error | YES (alloc ref) | NO (no put on candidate) | ❌ LEAK | kfree(candidate) without releasing ref. |
| L282 out (creating success, candidate non‑NULL) | success | YES | NO | ❌ LEAK | candidate freed without put. |
| L282 out (create_failed, candidate non‑NULL) | error | YES | NO | ❌ LEAK | candidate freed without put. |
| L282 out (any path, candidate NULL) | success/error | NO (candidate NULL) | N/A | ✅ | candidate consumed by install or already NULL. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`afs_alloc_server()` unconditionally sets the refcount (as per contract). When `afs_install_server()` returns an existing server instead of installing the candidate, `candidate` still holds that reference but is `kfree()`ed without a corresponding `afs_put_server()` (or equivalent), leaking the ref.
```
