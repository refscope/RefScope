# REAL BUG: net/sched/sch_htb.c:2068 htb_change_class()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| existing class: modify success → return 0 | L2068 | return 0 | no | no | yes (NULL) | same NULL issue, but refcount OK |

## Full Response

```
| Path Description | Line | Return Type | parent_qdisc? | old_q put? | qdisc_put(parent_qdisc) | Notes |
|------------------|------|-------------|---------------|------------|-------------------------|-------|
| opt null → failure | L1768 | error | no | no | no | ✅ |
| nla_parse fails → failure | L1775 | error | no | no | no | ✅ |
| tb[TCA_HTB_PARMS] null → failure | L1780 | error | no | no | no | ✅ |
| rate/ceil zero → failure | L1786 | error | no | no | no | ✅ |
| offload overhead/mpu → failure | L1794 | error | no | no | no | ✅ |
| classid invalid/depth → failure | L1817 | error | no | no | no | ✅ |
| kzalloc fails → failure | L1822 | error | no | no | no | ✅ |
| tcf_block_get err → kfree; failure | L1828 | error | no | no | no | ✅ |
| gen_new_estimator err → err_block_put | L1849 | error | no | no | no | ✅ |
| offload Assign-queue err → err_kill_estimator | L1890 | error | no | no | no | ✅ |
| offload First-child err (restore old_q) → err_kill_estimator | L1907 | error | no | no (restored) | no | ✅ |
| **offload First-child success → new class → leaf→inner → success return** | **L2068** | **return 0** | **yes** | **yes** (qdisc_put on old_q) | **yes** | **❌ DOUBLE PUT** – same qdisc released twice (old_q + parent_qdisc) |
| non-offload leaf→inner new class → success return | L2068 | return 0 | yes | no | yes | ✅ single put |
| non-offload parent not leaf → success return | L2068 | return 0 | no | no | yes (NULL) | ⚠️ possible NULL deref, but not a refcount excess |
| existing class: gen_replace_estimator err → return | L1984 | error | no | no | no | ✅ |
| existing class: offload modify err → return | L2008 | error | no | no | no | ✅ |
| existing class: modify success → return 0 | L2068 | return 0 | no | no | yes (NULL) | same NULL issue, but refcount OK |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
In the “First child” offload success path, `qdisc_put(old_q)` already releases the leaf Qdisc, but `parent->leaf.q` is not cleared; later `parent_qdisc = parent->leaf.q` and `qdisc_put(parent_qdisc)` cause a double put, triggering the refcount excess underflow.
```
