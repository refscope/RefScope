# REAL BUG: net/netfilter/nf_conntrack_netlink.c:3473 ctnetlink_del_expect()

**Confidence**: HIGH | **Counter**: `$->use.refs.counter`

## Reasoning

hrough) | success (return 0) | YES | see below | ❌ **BUG** | When `timer_delete` returns true: `nf_ct_unlink_expect_report` (does a put) + `nf_ct_expect_put` inside if + `nf_ct_expect_put` after spin_unlock → **3 puts for 2 references** (count 2→1→0‑→‑1), underflow. When false → 1 put, balanced. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3423 | error (return err) | NO (before get) | N/A | ✅ | |
| L3428 | error (return err) | NO (before get) | N/A | ✅ | |
| L3435 | error (!exp, return -ENOENT) | NO (conditional get failed) | N/A | ✅ | `nf_ct_expect_find_get` returned NULL → no ref held |
| L3442 | error (ID mismatch, return -ENOENT) | YES | YES (1 `nf_ct_expect_put`) | ✅ | explicit put balances the get |
| L3452 (implicit after first branch + fall‑through) | success (return 0) | YES | see below | ❌ **BUG** | When `timer_delete` returns true: `nf_ct_unlink_expect_report` (does a put) + `nf_ct_expect_put` inside if + `nf_ct_expect_put` after spin_unlock → **3 puts for 2 references** (count 2→1→0‑→‑1), underflow. When false → 1 put, balanced. |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
In the `timer_delete` true path, `nf_ct_unlink_expect_report` (which calls `nf_ct_expect_put`) is immediately followed by an extra `nf_ct_expect_put` inside the `if` block, then a third `nf_ct_expect_put` after spin_unlock. This results in a double‑put (refcount underflow) – a clear refcounting imbalance.
```
