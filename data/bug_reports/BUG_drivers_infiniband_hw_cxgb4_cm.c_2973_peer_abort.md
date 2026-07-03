# REAL BUG: drivers/infiniband/hw/cxgb4/cm.c:2973 peer_abort()

**Confidence**: MEDIUM | **Counter**: `$->refcount.refs.counter`

## Reasoning

[NEED_SOURCE] get_ep_from_tid (to verify reference acquisition)

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2822 | return 0 (ep NULL) | NO | N/A | ✅ | get_ep_from_tid returned NULL, no reference held |
| L2830 | goto deref_ep (neg advice) | YES (caller ref) + YES (get_ep_from_tid ref)** | 2x c4iw_put_ep at deref_ep | ✅ if release_ep_resources not involved | No extra get inside function |
| L2920 | goto deref_ep (DEAD state) | same as above | 2x c4iw_put_ep | ✅ if release_ep_resources not involved | No extra get |
| L2950‑L2960 (after switch, rpl_skb missing → out) | goto out with release=1 | same initial refs | release_ep_resources() (?) + 2x c4iw_put_ep | ❌ likely LEAK/EXCESS | If release_ep_resources drops ep ref, total puts > refs |
| L2965 (after switch, state!=ABORTING, !retry_with_mpa_v1) | normal path to out with release=1, skb OK | same | release_ep_resources() + 2x c4iw_put_ep | ❌ EXCESS if release_ep_resources puts |
| L2965‑L2970 (after switch, state==ABORTING, skb missing) | release=1 path | initial + c4iw_get_ep (+1 extra in FPDU_MODE) | release_ep_resources() + 2x c4iw_put_ep | ❌ EXCESS (3 puts for 3 refs? actually extra get = 3 refs, release_ep_resources may put, then 2 puts = total puts > 3) | complex |
| L2970 (fall through to deref_ep on retry path) | release=0, retry_with_mpa_v1 | initial refs | 2x c4iw_put_ep | ✅ | release_ep_resources not called |

**Assumptions needed:**
- `get_ep_from_tid()`: unclear if it acquires a reference. Likely does (common pattern), but not confirmed. If it does NOT, then all non‑NULL paths have only caller’s ref and two puts → excess put.
- `release_ep_resources()`: likely releases resources and possibly the ep reference (c4iw_put_ep). If it does, then any path where `release=1` causes triple put (caller ref + get_ep_from_tid ref + release_ep_resources internal put + two explicit puts). That matches the “excess put” warning.

Because the warning is a runtime refcount underflow, the bug is likely the double put after calling `release_ep_resources`. The locus of the warning (line 2973, the second `c4iw_put_ep` at `deref_ep`) is executed after `release_ep_resources`, making it the superfluous put.

[NEED_SOURCE] get_ep_from_tid (to verify reference acquisition)
[NEED_SOURCE] release_ep_resources (to verify if it drops ep reference)

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
In paths where `release = 1` and `release_ep_resources(ep)` is called, the subsequent double `c4iw_put_ep(&ep->com)` at `deref_ep` causes an excess put if `release_ep_resources` already drops the ep reference. Full confirmation requires the internals of `release_ep_resources`.
```
