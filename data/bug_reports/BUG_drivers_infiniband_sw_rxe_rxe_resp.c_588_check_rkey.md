# REAL BUG: drivers/infiniband/sw/rxe/rxe_resp.c:588 check_rkey()

**Confidence**: HIGH | **Counter**: `$->ref_cnt.refcount.refs.counter`

## Reasoning

| L552 | return RESPST_EXECUTE (success) | YES/NO | NO (mr stored in qp->resp.mr) | ✅ (ownership transfer) | If get failed, stored pointer is dangling; refcount leak not visible here. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L481 | return RESPST_EXECUTE (zero‑byte early) | NO (no get) | N/A | ✅ | before any refcount operation |
| L495 | goto err (mw == NULL) | NO (no get) | NO (mr NULL, mw NULL) | ✅ | no reference held |
| L501 | goto err (mr == NULL, mw non‑NULL) | NO (get not yet called) | YES (mw put) | ✅ | mw reference from lookup released |
| L520 | goto skip_check_range (flush MR) → success later | YES (rxe_get called) | NO (mr stored, ownership transferred) | ✅ (see note) | **If rxe_get failed**: mr stored without ref → use‑after‑free later. For this path, put not reached. |
| L525 | goto err after mr_check_range | YES (rxe_get called) | YES (rxe_put(mr) at err) | ❌ **EXCESS PUT** if rxe_get failed | **rxe_get return value unchecked**; on failure ref not taken but put executed → refcount underflow |
| L531 | goto err (ATOMIC_WRITE length fail) | YES | YES | ❌ same as above | same rxe_get issue |
| L537 | goto err (WRITE mtu fail) | YES | YES | ❌ same | same |
| L542 | goto err (WRITE resid length fail) | YES | YES | ❌ same | same |
| L546 | goto err (WRITE pad fail) | YES | YES | ❌ same | same |
| L552 | return RESPST_EXECUTE (success) | YES/NO | NO (mr stored in qp->resp.mr) | ✅ (ownership transfer) | If get failed, stored pointer is dangling; refcount leak not visible here. |

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  
`rxe_get(mr)` is a conditional get (same semantics as `__rxe_get` → `kref_get_unless_zero`), but its return value is ignored. In the MW branch, after calling `rxe_get`, every error path that jumps to `err` will unconditionally execute `rxe_put(mr)`. If `rxe_get` returned zero (reference **not** taken), the put becomes an extra decrement on a refcount that may already be zero, causing exactly the “refcount excess put” warning at line 588. The fix is to check the return value of `rxe_get` and, on failure, skip the `rxe_put(mr)` (and treat the mr as invalid, e.g., `mr = NULL` or return an error).
```
