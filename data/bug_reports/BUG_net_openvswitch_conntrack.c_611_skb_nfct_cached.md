# REAL BUG: net/openvswitch/conntrack.c:611 skb_nfct_cached()

**Confidence**: HIGH | **Counter**: `$->ct_general.use.refs.counter`

## Reasoning

To definitively rule out that `ovs_ct_executed` might return only conntracks that pass all subsequent checks, I have requested its source. Pending that, the code as written is clearly broken.

## Full Response

```
| Line (approx) | Return Type | GET from ovs_ct_executed? | PUT Done? | Balanced? | Notes |
|----------------|-------------|---------------------------|-----------|-----------|-------|
| after `if (!ct)` check, `else return false` (ct=NULL) | false       | NO (ct is NULL)           | N/A       | ✅         | No reference held |
| after `net_eq` check: `return false;`                       | false       | YES (if ct from ovs_ct_executed) / NO (if from skb) | NO        | ❌ LEAK if ct from ovs | Missing `nf_ct_put()` on this path |
| after zone check: `return false;`                           | false       | same as above             | NO        | ❌ LEAK if ct from ovs | Missing `nf_ct_put()` |
| helper mismatch: `return false;`                            | false       | same                      | NO        | ❌ LEAK if ct from ovs | Missing `nf_ct_put()` |
| timeout mismatch/ext not found: `return false;`            | false       | same                      | NO        | ❌ LEAK if ct from ovs | Missing `nf_ct_put()` |
| force block: `nf_ct_delete`/`nf_ct_put` + `return false;`   | false       | YES (if ct from ovs) / NO (if from skb) | YES (`nf_ct_put()`) | ⚠️ **OVER-PUT** if ct from skb | `nf_ct_put()` on a reference we don't own would underflow |
| final `return ct_executed;` (no earlier return)             | true/false  | YES (if ct from ovs) / NO (if from skb) | NO        | ❌ LEAK if ct from ovs | Reference is not stored anywhere; caller cannot release |

**Observation:** The function acquires a reference via `ovs_ct_executed()` when the skb lacks a conntrack, but only releases it in the `info->force` block. All other `return false` paths, and the final `return ct_executed`, leak the reference when `ct` originated from `ovs_ct_executed`. Conversely, when `ct` comes from the skb (no extra reference), the force block does an unwarranted `nf_ct_put()` leading to an underflow. This asymmetry is the “inconsistent refcounting” smatch detected.

To definitively rule out that `ovs_ct_executed` might return only conntracks that pass all subsequent checks, I have requested its source. Pending that, the code as written is clearly broken.

[NEED_SOURCE] ovs_ct_executed   **_(but verdict is not blocked by this)_**

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
The function lacks matching `nf_ct_put()` on most error/return paths when `ovs_ct_executed()` succeeds, leaking a conntrack reference. The sole `nf_ct_put()` in the force block also risks an underflow if `ct` came from the skb.
```
