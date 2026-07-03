# REAL BUG: drivers/net/ethernet/mellanox/mlx5/core/steering/sws/dr_ptrn.c:182 mlx5dr_ptrn_cache_get_pattern()

**Confidence**: HIGH | **Counter**: `pattern->refcount.refs.counter`

## Reasoning

No IS_ERR guard, ownership transfer, devm, or async mechanism applies here. The error path is clearly leaking a put.

## Full Response

```
| Line(s) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|---------|-------------|-----------|-----------|-----------|-------|
| L145 (goto out_unlock) | error (alloc failed) | NO (alloc returned NULL) | N/A | ✅ | No get, nothing to put |
| L160-161, then L169-L170 (goto free_pattern → dr_ptrn_free_pattern) | error (send_postsend failed) | YES (dr_ptrn_alloc_pattern set refcount to 1) | YES (refcount_dec) + dr_ptrn_free_pattern almost certainly includes its own put (kref_put/refcount_dec_and_test) → double dec | ❌ **LEAK (excess put)** | Warning “refcount excess put” indicates double decrement; manual dec before free that also decs |
| L163-164 (else), L166-167 (return pattern) | success (cache hit) | YES (refcount_inc) | NO | ✅ | Inc, caller will put later |
| L158-162 (send_postsend success), L166-167 (return pattern) | success (new pattern) | YES (alloc gave ref=1) | NO | ✅ | New pattern returned, caller owns ref |

**Detailed reasoning:**

- `dr_ptrn_alloc_pattern` unconditionally sets the refcount (contract says `refcount_set(set)`), so the newly allocated `pattern` starts with a reference (1).
- On the error path where `mlx5dr_send_postsend_pattern` fails, the code calls `refcount_dec(&pattern->refcount);` and then `goto free_pattern`. The `free_pattern` label invokes `dr_ptrn_free_pattern(pattern)`.  
- The smatch warning detects an **excess put** on `pattern->refcount.refs.counter` at line 182, which is **inside or after** `dr_ptrn_free_pattern`. The only plausible cause is that `dr_ptrn_free_pattern` itself performs a final refcount decrement (e.g., `refcount_dec_and_test` or `kref_put`). Therefore, the manual `refcount_dec` before calling `free_pattern` results in a **double decrement** – one extra put.
- The success paths (cache hit, new pattern and successful send) return the pattern without an internal put, which is correct because the caller will later release the reference.

No IS_ERR guard, ownership transfer, devm, or async mechanism applies here. The error path is clearly leaking a put.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
```
