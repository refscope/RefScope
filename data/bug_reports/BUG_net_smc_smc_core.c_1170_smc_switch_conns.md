# REAL BUG: net/smc/smc_core.c:1170 smc_switch_conns()

**Confidence**: HIGH | **Counter**: `$->__sk_common.skc_refcnt.refs.counter`

## Reasoning

**Leak path**: `sock_hold` → `smc_cdc_get_free_slot` fails with rc ≠ 0 → `goto err_out` (L1152) → `err_out` → return NULL, missing `sock_put`.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1121 | error       | NO (before any hold)   | N/A  | ✅ | to_lnk not found or hold failed; no sock_hold |
| L1152 (goto err_out) | error | YES (sock_hold at L1147) | NO   | ❌ LEAK | sock_hold held, but `err_out` label has no `sock_put` |
| L1160 (goto err_out) | error | YES (sock_hold)         | YES (sock_put at L1158) | ✅ | `sock_put` executed before `goto` |
| L1165 | success | YES only if loop ran any hold* | YES (all puts paired before `goto again`) | ✅ | if any hold was taken, it was released before re-loop; no outstanding hold at normal exit |

**\*** For L1165: if the loop never entered the `sock_hold` branch, GET=NO and it’s still balanced.  
**Leak path**: `sock_hold` → `smc_cdc_get_free_slot` fails with rc ≠ 0 → `goto err_out` (L1152) → `err_out` → return NULL, missing `sock_put`.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`smc_switch_conns` takes an unconditional socket reference with `sock_hold` at line 1147. If the subsequent `smc_cdc_get_free_slot` fails (rc != 0), the function jumps to `err_out` and returns NULL without calling `sock_put`, leaking a socket refcount.
```
