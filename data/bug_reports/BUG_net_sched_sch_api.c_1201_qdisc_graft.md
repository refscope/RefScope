# REAL BUG: net/sched/sch_api.c:1201 qdisc_graft()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

This double put triggers “refcount excess put” at line 1201, likely inside `qdisc_destroy` itself.

## Full Response

```
| Line | Return Type | Old Ingress Qdisc PUTs? | Excess? | Notes |
|------|-------------|-------------------------|---------|-------|
| L1106 (if !dev_queue) | error (–ENOENT) | NO (dec_if_one not reached) | safe | Early return before any put on ingress qdisc |
| L1112 (dec_if_one fails) | error (–EBUSY) | NO (dec_if_one returns false, no decrement) | safe | Function returns immediately, no further operations on the qdisc |
| L1174 (cops/graft missing) | error (–EOPNOTSUPP) | N/A (else block, no ingress handling) | N/A | |
| L1179 (class not found) | error (–ENOENT) | N/A | N/A | |
| L1184 (noqueue check) | error (–EINVAL) | N/A | N/A | |
| L1191 (stab check) | error (–EINVAL) | N/A | N/A | |
| L1195 (cops->graft err) | error (err) | N/A | N/A | |
| L1198 (ingress path → return 0) | success | PUT#1 (qdisc_refcount_dec_if_one) + PUT#2 (qdisc_destroy) | ❌ EXCESS PUT | dec_if_one succeeds → refcount 0 → later qdisc_destroy calls another put → refcount underflow |

**Detail on the excess put path**:  
When `parent == NULL` and the ingress flag is set, `qdisc_refcount_dec_if_one(q)` on the old ingress qdisc succeeds (refcount becomes 0).  
Later, at L1137–L1144, `qdisc_destroy(old)` is called on the same qdisc, which puts again (refcount goes negative).  
This double put triggers “refcount excess put” at line 1201, likely inside `qdisc_destroy` itself.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`qdisc_refcount_dec_if_one` already takes the last reference; subsequent `qdisc_destroy` on the same qdisc causes a put on a zero refcount, leading to an excess put.
```
