# REAL BUG: net/ipv4/igmp.c:1149 igmp_rcv()

**Confidence**: MEDIUM | **Counter**: `$->refcnt.refs.counter`

## Reasoning

ontracts indicate contains both GET and PUT operations mapped to `__in_dev_put`. The imbalance (excess put without a corresponding get) must reside inside `igmp_heard_query()` and is reflected at the caller’s return point. Since `igmp_rcv` itself is not the source of the leak, the callee is buggy.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1097 | goto drop   | NO        | NO        | ✅ | __in_dev_get_rcu (RCU), no ref held |
| L1101 | goto drop   | NO        | NO        | ✅ | |
| L1103 | goto drop   | NO        | NO        | ✅ | |
| L1105 | goto drop   | NO        | NO        | ✅ | |
| L1109-1110 (IGMP_HOST_MEMBERSHIP_QUERY) | fall through to drop, return 0 | NO* | NO* | ✅* | *get/put happen inside igmp_heard_query(); igmp_rcv itself does not change in_dev refcount |
| L1149 (IGMP_PIM, early return) | return pim_rcv_v1(skb) | NO | NO | ✅ | no in_dev operation |
| other switch cases (fall through) | break to drop, return 0 | NO | NO | ✅ | |
| drop label (L1150+) | return 0 after kfree/consume | NO | NO | ✅ | |

**Note:** All return paths of `igmp_rcv` are balanced with respect to `in_dev->refcnt` because `igmp_rcv` never acquires or releases a reference. The `in_dev` is accessed via `__in_dev_get_rcu` (RCU-only, no refcount increment). The warning about an excess put on `in_dev->refcnt.refs.counter` at line 1149 originates from `igmp_heard_query()` (called at L1109), which the contracts indicate contains both GET and PUT operations mapped to `__in_dev_put`. The imbalance (excess put without a corresponding get) must reside inside `igmp_heard_query()` and is reflected at the caller’s return point. Since `igmp_rcv` itself is not the source of the leak, the callee is buggy.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`igmp_heard_query()` has an internal refcount mismatch (conditional get, unmatched put) causing an excess put on `in_dev`; the warning line indicates the caller where the imbalance manifests.
```
