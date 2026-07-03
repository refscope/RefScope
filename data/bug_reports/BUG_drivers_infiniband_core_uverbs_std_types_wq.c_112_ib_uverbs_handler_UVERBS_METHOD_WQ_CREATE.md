# REAL BUG: drivers/infiniband/core/uverbs_std_types_wq.c:112 ib_uverbs_handler_UVERBS_METHOD_WQ_CREATE()

**Confidence**: LOW | **Counter**: `obj->uevent.event_file->uobj.ref.refcount.refs.counter`

## Reasoning

ented ownership transfer that would absolve this path (the `uobj` structure might take ownership, but that would require the `uobj` itself to be properly released on error; the inconsistent refcounting flag suggests that even if `uobj` is being freed, the event_file’s refcount is still off).

## Full Response

```
[NEED_SOURCE] ib_uverbs_handler_UVERBS_METHOD_WQ_CREATE

**Note:** Full source for `ib_uverbs_handler_UVERBS_METHOD_WQ_CREATE()` is not available. Analysis is based on the warning, contracts, and typical handler patterns. Path table covers only the known leaking line (L112). All other return paths cannot be enumerated without source.

## Path Table
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L112 | error       | YES (ib_uverbs_get_async_event succeeded before this point) | NO   | ❌ LEAK | Warning: "inconsistent refcounting" on `obj->uevent.event_file->uobj.ref` at this line implies a path where the get was done but the matching `uverbs_uobject_put()` (or equivalent) was not executed |

**GET semantics:** `ib_uverbs_get_async_event()` is conditional – it increments the refcount **only** on success (returns a non-NULL pointer). If it returned non-NULL earlier in the function, a reference was taken and held in `obj->uevent.event_file`. That reference must be released by `uverbs_uobject_put()` (or via `uobj` cleanup) on every subsequent path that leaves the function without storing the pointer in a long-lived context that guarantees future release.

**Warning analysis:** The counter `obj->uevent.event_file->uobj.ref.refcount.refs.counter` is unbalanced at line 112. Since the get occurred before this line, the function is returning without the required put. There is no evidence of a documented ownership transfer that would absolve this path (the `uobj` structure might take ownership, but that would require the `uobj` itself to be properly released on error; the inconsistent refcounting flag suggests that even if `uobj` is being freed, the event_file’s refcount is still off).

**PRE-VERDICT CHECKLIST:**
1. **"Held for device lifetime"?** Not applicable; no indication that L112 is the successful probe path. It is an error return, and such “held for lifetime” claims do not cover error paths.  
2. **"Ownership transferred"?** Even if ownership is transferred to `uobj`, the error path must release `uobj` (which would then put the event_file). The warning states the counter is inconsistent, implying that the `uobj` cleanup is either absent or does not handle the put correctly on this path. No verifiable cleanup code is provided → assume no reliable transfer.  
3. **Unconditional GET?** GET is conditional, but it succeeded earlier (otherwise the event_file pointer would be NULL/ERR and no counter would be touched). So GET=YES on this path.  
4. **goto out between GET and PUT?** Without source, cannot trace, but the wartning line itself is the problematic return point; any preceding label presumably lacks the put.

With the GET executed and no PUT on this error path, the refcount remains elevated, causing the reported imbalance. Therefore:

VERDICT: REAL_BUG  
CONFIDENCE: LOW  
(The source is missing; confidence is low because the exact control flow cannot be verified.
```
