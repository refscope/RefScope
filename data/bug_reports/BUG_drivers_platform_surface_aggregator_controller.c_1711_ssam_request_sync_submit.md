# REAL BUG: drivers/platform/surface/aggregator/controller.c:1711 ssam_request_sync_submit()

**Confidence**: HIGH | **Counter**: `rqst->base.packet.refcnt.refcount.refs.counter`

## Reasoning

4. goto out – No goto; the paths are explicit.

## Full Response

```
| Line | Return Type   | GET Done? | PUT Done? | Balanced? | Notes |
|------|---------------|-----------|-----------|-----------|-------|
| L1705 | error (`-ENODEV`) | NO (before `ssh_rtl_submit`) | YES | ✅ | Caller’s reference correctly released; no get happened. |
| L1712 (status < 0) | error (submit failed) | NO (conditional get NOT called on failure) | YES | ✅ | Caller’s reference released; no extra get. |
| L1712 (status >= 0) | success (submit succeeded) | YES (conditional get from `ssh_rtl_submit`) | YES | ❌ LEAK | GET +1, PUT -1 ⇒ net 0. The caller’s reference is **not** released, so it leaks. |

**Pre‑verdict checklist**  
1. “Held for device lifetime” – Does not apply here.  
2. “Ownership transferred” – No evidence of ownership transfer; the function still does a `put`, and the get inside `ssh_rtl_submit` is unconditional *on success*.  
3. Unconditional GET – The get is conditional (only on success). Success path does GET + PUT = net 0, but the function’s contract is to **consume the caller’s reference** (as seen on the error paths). Hence the success path fails to release it.  
4. goto out – No goto; the paths are explicit.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`ssh_rtl_submit` conditionally calls `ssh_request_get` on success. The function then always calls `ssh_request_put`, but on success this `put` only cancels the internal get, leaving the caller’s reference undecremented → refcount leak.
```
