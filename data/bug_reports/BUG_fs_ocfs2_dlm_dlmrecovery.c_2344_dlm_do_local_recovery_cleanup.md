# REAL BUG: fs/ocfs2/dlm/dlmrecovery.c:2344 dlm_do_local_recovery_cleanup()

**Confidence**: HIGH | **Counter**: `$->refs.refcount.refs.counter`

## Reasoning

| All other paths | continue/end | NO | NO | ✅ | No puts on `res` in these branches. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2365-2369 (recovery lock, owner dead_node & DROPPING_REF) | continue | YES (dlm_lockres_get at L2365) | YES (dlm_lockres_put at L2369) + possibly put inside __dlm_do_purge_lockres (L2366) | ❌ | If purge calls put, net puts may exceed get; excess put possible. |
| L2387-2391 (non‑recovery lock, owner dead_node & DROPPING_REF) | continue | YES (L2387) | YES (L2391) + possibly put in __dlm_do_purge_lockres (L2388) | ❌ | Same double‑put risk. |
| L2396‑2397 (owner == dlm->node_num) | continue/end | NO (no get) | YES **conditional** (__dlm_lockres_calc_usage may call dlm_lockres_put after dlm_free_dead_locks drops refcount to 0) | ❌ LEAK/EXCESS | dlm_free_dead_locks can drop last references; subsequent __dlm_lockres_calc_usage may put on zero refcount → excess put. |
| All other paths | continue/end | NO | NO | ✅ | No puts on `res` in these branches. |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

In the `res->owner == dlm->node_num` branch (non‑recovery locks, after the false side of line 2344), `dlm_free_dead_locks` may drop all locks, bringing the resource’s refcount to zero. Then `__dlm_lockres_calc_usage` — which can call `dlm_lockres_put` — is invoked, causing a put on a zero refcount (excess put). The warning correctly pinpoints the entry into this path at line 2344.
```
