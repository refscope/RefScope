# REAL BUG: crypto/api.c:367 crypto_alg_mod_lookup()

**Confidence**: HIGH | **Counter**: `$->cra_refcnt.refs.counter`

## Reasoning

e contract for `crypto_larval_wait` only mentions `crypto_mod_get`/`crypto_mod_put` for the returned algorithm, not for the larval argument. The explicit put in the `else` branch strongly suggests the caller owns the larval reference and must release it. Therefore the NOTIFY_STOP path is a leak. |

## Full Response

```
| Line | Return Type | GET Done? (larval ref from lookup) | PUT Done? | Balanced? | Notes |
|------|-------------|------------------------------------|-----------|-----------|-------|
| L355 | return larval (IS_ERR or !crypto_is_larval) | If !IS_ERR and not larval: reference taken by `crypto_larval_lookup` on the returned alg. | No explicit put – ownership transferred to caller. Caller is responsible for releasing. | ✅ | Not a leak in this function; the reference is handed back to the caller. |
| L361‑L365 (else path, `ok != NOTIFY_STOP`) | `crypto_mod_put(larval)`, then `alg = ERR_PTR(-ENOENT)`, kill, return alg. | Larval reference from lookup is held. | YES – `crypto_mod_put(larval)` explicitly releases it. | ✅ | |
| L359‑L365 (NOTIFY_STOP path) | `alg = crypto_larval_wait(larval, type, mask)`, kill, return alg. | Larval reference from lookup is held. `crypto_larval_wait` may acquire a new reference on the returned `alg`. | NO explicit `crypto_mod_put(larval)` on this path. | ❌ | Larval reference leaked unless `crypto_larval_wait` internally consumes it. The contract for `crypto_larval_wait` only mentions `crypto_mod_get`/`crypto_mod_put` for the returned algorithm, not for the larval argument. The explicit put in the `else` branch strongly suggests the caller owns the larval reference and must release it. Therefore the NOTIFY_STOP path is a leak. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the NOTIFY_STOP path, `crypto_larval_wait()` returns without the caller releasing the `larval` reference obtained from `crypto_larval_lookup()`, while the `else` branch correctly calls `crypto_mod_put(larval)`. This leaks the `larval` object’s `cra_refcnt`. `[NEED_SOURCE] crypto_larval_wait` would definitively confirm that the larval reference is not dropped internally.
```
