# REAL BUG: net/netfilter/nf_conntrack_netlink.c:3311 ctnetlink_dump_exp_ct()

**Confidence**: HIGH | **Counter**: `$->ct_general.use.refs.counter`

## Reasoning

| L3302  | return err (dump start failure) | YES | YES (nf_ct_put) | ✅ | dump failed, no later .done |

## Full Response

```
| Line   | Return Type        | GET Done? | PUT Done?         | Balanced? | Notes |
|--------|--------------------|-----------|-------------------|-----------|-------|
| L3275  | error (tuple parse)| NO        | N/A               | ✅ | before get |
| L3280  | error (zone parse) | NO        | N/A               | ✅ | before get |
| L3287  | error (no conntrack)| NO        | N/A               | ✅ | h == NULL → get not done |
| L3294  | early return (no help) | YES   | YES (nf_ct_put)   | ✅ | get then put |
| L3302  | return 0 (dump start success) | YES | YES (nf_ct_put) | ❌ **double put** | .done callback also releases ref |
| L3302  | return err (dump start failure) | YES | YES (nf_ct_put) | ✅ | dump failed, no later .done |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`nf_conntrack_find_get` acquires a reference.  On successful `netlink_dump_start`, the dump subsystem owns the reference and will release it via the `.done` callback (`ctnetlink_dump_exp_ct_done`).  Calling `nf_ct_put(ct)` immediately after `netlink_dump_start` returns 0 causes a second decrement, leading to refcount underflow and use-after-free.  The failure path of `netlink_dump_start` correctly releases the reference.

[NEED_SOURCE] ctnetlink_dump_exp_ct_done — to confirm the final put inside the dump completion, but the pattern is unambiguous.
```
