# REAL BUG: net/netfilter/ipvs/ip_vs_core.c:593 ip_vs_sched_persist()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| ~570 | return cp (success) | YES (current ct ref) | YES (`ip_vs_conn_put(ct)`) | ✅ (for current ct) | Old ct (if check_template failed earlier) never released → **leak persists** |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~485 | return NULL (param fill failed) | NO (no ct) | N/A | ✅ | `ip_vs_conn_fill_param_persist` failure, no ref held. |
| ~505 | return NULL (no dest, ct == NULL) | NO (lookup returned NULL) | N/A | ✅ | `ip_vs_ct_in_get` returned NULL; no template ref. |
| ~505 | return NULL (no dest, ct != NULL) | **YES** (ct ref from `ip_vs_ct_in_get`, check_template failed) | **NO** | ❌ **LEAK** | Old template reference leaked; `ip_vs_conn_put` never called. |
| ~520 | return NULL (template create fails, ct == NULL) | NO (no old ct) | N/A | ✅ | `ip_vs_ct_in_get` returned NULL; new template alloc failed. |
| ~520 | return NULL (template create fails, ct != NULL) | **YES** (ct ref from `ip_vs_ct_in_get`) | **NO** | ❌ **LEAK** | Old template ref lost when new alloc fails; no `ip_vs_conn_put`. |
| ~550 | return NULL (cp create fails) | YES (current ct ref) | YES (`ip_vs_conn_put(ct)`) | ✅ (for current ct) | Old ct leak (if any) remains; this return releases current ct. |
| ~570 | return cp (success) | YES (current ct ref) | YES (`ip_vs_conn_put(ct)`) | ✅ (for current ct) | Old ct (if check_template failed earlier) never released → **leak persists** |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

When `ip_vs_ct_in_get` returns a non-NULL template but `ip_vs_check_template` fails, the obtained reference is never released. The code enters the `if` block, might look for a new destination, and either bails out without `ip_vs_conn_put` or creates a new template, overwriting the old pointer and leaking its refcount.
```
