# REAL BUG: net/sunrpc/clnt.c:3236 rpc_xprt_offline()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L3232‑3234 | **out** label: xprt_put(xprt); xprt_switch_put(xps); return err | (already covered) | YES | ❌ if GET failed | final put, no guard for failed get |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3222 | goto out (err non‑zero after addr compare) | YES if xprt_get succeeded; NO if failed | YES (xprt_put at L3232) | ❌ if GET failed (over‑put) | xprt_get return ignored, unconditionally put |
| L3226 | goto out (wait‑on‑bit‑lock error) | same as above | YES | ❌ if GET failed | same |
| L3230‑3231 | fall through → out, return 0 | same | YES | ❌ if GET failed | success path, same unconditional put |
| L3232‑3234 | **out** label: xprt_put(xprt); xprt_switch_put(xps); return err | (already covered) | YES | ❌ if GET failed | final put, no guard for failed get |

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  
`xprt_get` returns `NULL` on failure, but the function ignores the return value and always calls `xprt_put(xprt)`. If the get fails, the put over‑decrements the refcount, leading to an inconsistent refcount (underflow/double‑free) — a real bug per the contract.
```
