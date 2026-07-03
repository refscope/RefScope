# REAL BUG: net/smc/smc_llc.c:1319 smc_llc_delete_asym_link()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L1314   | fall‑through to out_free | NO                    | YES                     | ❌ EXCESS PUT | success path; clear called without ever having taken a ref on `lnk_asym`. |

## Full Response

```
```
| Line    | Return Type          | GET Done?             | PUT Done?               | Balanced?     | Notes                                                                 |
|---------|----------------------|-----------------------|-------------------------|---------------|-----------------------------------------------------------------------|
| L1294   | early return         | NO (no get)           | N/A                     | ✅            | `lnk_asym` is NULL; no ref held.                                      |
| L1296   | early return         | NO (no get)           | N/A                     | ✅            | link not in downing state; no ref held.                               |
| L1299   | goto out_free        | NO (no get on lnk_asym) | YES (`smcr_link_clear`) | ❌ EXCESS PUT | `smc_switch_conns()` returned NULL; clear called without a matching ref. |
| L1307   | goto out_free        | NO                    | YES                     | ❌ EXCESS PUT | `smc_llc_send_delete_link()` error path; clear called without get.    |
| L1312   | goto out_free        | NO                    | YES                     | ❌ EXCESS PUT | `smc_llc_wait()` returns NULL; clear called without get.              |
| L1314   | fall‑through to out_free | NO                    | YES                     | ❌ EXCESS PUT | success path; clear called without ever having taken a ref on `lnk_asym`. |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`smcr_link_clear(lnk_asym, true)` is called in every path that reaches `out_free`, but the function never acquires a reference on `lnk_asym` (neither via `smc_llc_find_asym_link` nor `smc_switch_conns`), causing a refcount underflow.
```
```
