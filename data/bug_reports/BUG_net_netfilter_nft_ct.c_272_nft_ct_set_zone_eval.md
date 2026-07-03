# REAL BUG: net/netfilter/nft_ct.c:272 nft_ct_set_zone_eval()

**Confidence**: HIGH | **Counter**: `ct->ct_general.use.refs.counter`

## Reasoning

unter is not incremented, but the unconditional `refcount_dec(&ct->ct_general.use)` in the `else` branch still executes, causing a decrement without a corresponding increment—a refcount excess put. This is a real bug because under the right (admittedly rare) condition, it can corrupt the refcount.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L236 | early return | NO (before any get) | N/A  | ✅ | Packet already tracked, no ref acquired. |
| L264 | error (alloc fail) | YES (template ct via `__refcount_inc`, **if it succeeded**) / **NO (if `__refcount_inc` failed)** | YES (unconditional `refcount_dec` in else branch) | ❌ **UNBALANCED when `__refcount_inc` fails** — dec without prior inc → excess put. | This path enters the `else` branch where `refcount_dec` is called unconditionally. `__refcount_inc` is a conditional get: it only increments if the counter is not `REFCOUNT_MAX`. On failure, no increment occurs but the dec still runs, leading to an excess put. |
| L270 | success (void return) | YES (template inc if `oldcnt==1`, or new ct ref from `nf_ct_tmpl_alloc`) | NO (ownership transferred to skb) | ✅ for normal case, but **excess put on template ct if `__refcount_inc` failed and `oldcnt!=1`** (the dec still executes). | The template ct’s dec is unconditional in the `else` branch, regardless of alloc success. If `__refcount_inc` failed, the dec is unbalanced. |

**Reasoning:** The call to `__refcount_inc(&ct->ct_general.use, &oldcnt)` returns a boolean indicating success (true if counter was < REFCOUNT_MAX). The code ignores this return value and only checks `oldcnt`. If `__refcount_inc` fails (refcount already at maximum), the counter is not incremented, but the unconditional `refcount_dec(&ct->ct_general.use)` in the `else` branch still executes, causing a decrement without a corresponding increment—a refcount excess put. This is a real bug because under the right (admittedly rare) condition, it can corrupt the refcount.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`__refcount_inc` return not checked; unconditional `refcount_dec` in else branch can run without a prior increment, leading to a refcount excess put on the percpu template conntrack.
```
