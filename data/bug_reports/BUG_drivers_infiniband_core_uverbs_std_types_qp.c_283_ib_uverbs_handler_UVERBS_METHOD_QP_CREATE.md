# REAL BUG: drivers/infiniband/core/uverbs_std_types_qp.c:283 ib_uverbs_handler_UVERBS_METHOD_QP_CREATE()

**Confidence**: LOW | **Counter**: `obj->uevent.event_file->uobj.ref.refcount.refs.counter`

## Reasoning

- Common pattern in UVERBS QP create: after calling `ib_uverbs_get_async_event` (which bumps the ref), error paths later in the function may forget to release it, leading to a leak.

## Full Response

```
[NEED_SOURCE] ib_uverbs_handler_UVERBS_METHOD_QP_CREATE

## Path Table (approximated from contracts & warning context; source missing)

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L283 | error path (goto/return after successful get) | YES (ib_uverbs_get_async_event returned non‑NULL) | NO (uverbs_uobject_put not called on this path) | ❌ LEAK | Warning points here; counter is obj->uevent.event_file->uobj.ref.refcount.refs.counter |

**Reasoning:**
- `ib_uverbs_get_async_event()` is **conditional_on_nonnull** – if it returns non‑NULL, a kref is taken (via `uverbs_uobject_get`).
- Any path that obtains a valid event_file pointer **must** eventually call `uverbs_uobject_put()`.
- The warning shows an inconsistent refcount on the event_file’s kref at line 283, meaning on at least one return at/near that line the matching put is missing.
- Without the source, I cannot list every return; however, the default from Lesson “Default” applies: a GET contract exists and the warning says “refcount leak” → the indicated line likely returns without a put → REAL_BUG.
- Common pattern in UVERBS QP create: after calling `ib_uverbs_get_async_event` (which bumps the ref), error paths later in the function may forget to release it, leading to a leak.

**PRE-VERDICT CHECKLIST**
1. **Held for device lifetime?** – Not relevant here; event_file ref is not device‑lifetime on error paths.  
2. **Ownership transfer?** – If the event_file pointer is stored in the QP structure, cleanup would happen when the QP is freed, but that only covers the happy path. Error paths before the QP is fully constructed (before a valid `uobj->object`) do **not** trigger the QP’s destructor. Hence the ref must be explicitly put on those paths. The warning strongly suggests such a path exists.  
3. **Unconditional GET?** – No, it’s conditional, but once it succeeds, a ref is held.  
4. **goto out between GET and PUT?** – Likely, some `goto err` or `goto out` after the get misses the put. L283 is an error return that skips it.

VERDICT: REAL_BUG
CONFIDENCE: LOW (source missing; confident in pattern but need actual code to confirm all paths)
```
