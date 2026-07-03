# REAL BUG: net/sched/cls_api.c:2469 tc_new_tfilter()

**Confidence**: MEDIUM | **Counter**: `$->refcnt.refs.counter`

## Reasoning

code jumps to `errout_tp`, where `tp` is an error pointer and is not put; `tp_new` is never freed or put. Unless `tcf_chain_tp_insert_unique` internally calls `tcf_proto_put` on `tp_new` when insertion fails (source unknown), this is a real refcount leak.

## Full Response

```
| Path Description | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| Early return: prio==0, no NLM_F_CREATE | NO (no tp) | N/A | ✅ | |
| Early return: __tcf_qdisc_find error | NO | N/A | ✅ | |
| goto errout from tcf_proto_check_kind error | NO | N/A | ✅ | |
| goto errout from __tcf_qdisc_cl_find error | NO | N/A | ✅ | |
| goto errout from IS_ERR(block) | NO | N/A | ✅ | |
| goto errout from chain_index > limit | NO | N/A | ✅ | |
| goto errout from tcf_chain_get failure | NO | N/A | ✅ | |
| goto errout_locked → errout from IS_ERR(tp) after tcf_chain_tp_find | NO (IS_ERR) | N/A | ✅ | |
| goto errout_locked → errout from tp==NULL, chain->flushing | NO (tp NULL) | N/A | ✅ | |
| goto errout_locked → errout from tp==NULL, kind/proto missing | NO | N/A | ✅ | |
| goto errout_locked → errout from tp==NULL, no NLM_F_CREATE | NO | N/A | ✅ | |
| goto errout_tp from IS_ERR(tp_new) after tcf_proto_create | NO (IS_ERR) | N/A | ✅ | |
| goto errout_tp from IS_ERR(tp) after tcf_chain_tp_insert_unique | YES (tp_new from create) | NO | ❌ LEAK | tp_new refcount not released, insert_unique error path skips delete_empty and tp put |
| goto errout from existing or created tp on kind mismatch | YES | YES (via errout_tp put) | ✅ | |
| goto errout from fh==NULL, no NLM_F_CREATE | YES | YES | ✅ | |
| goto errout from NLM_F_EXCL with fh | YES | YES | ✅ | (tfilter_put does not affect tp ref) |
| goto errout from chain->tmplt_ops mismatch | YES | YES | ✅ | |
| tp->ops->change error, falls to errout (tp_created=1) | YES (tp_new) | YES (delete_empty + errout_tp put) | ✅ | |
| tp->ops->change error, falls to errout (tp_created=0) | YES (existing tp) | YES (errout_tp put) | ✅ | |
| success path: change returns 0, falls to errout (tp_created=1) | YES | YES (errout_tp put, no delete_empty) | ✅ | chain retains its reference |
| success path: change returns 0, tp_created=0 | YES | YES (errout_tp put) | ✅ | |

The only path where a tp reference (from tcf_proto_create) remains unreleased is the error path after `tcf_chain_tp_insert_unique` returns an error. The code jumps to `errout_tp`, where `tp` is an error pointer and is not put; `tp_new` is never freed or put. Unless `tcf_chain_tp_insert_unique` internally calls `tcf_proto_put` on `tp_new` when insertion fails (source unknown), this is a real refcount leak.

[NEED_SOURCE] tcf_chain_tp_insert_unique

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
When `tcf_chain_tp_insert_unique` fails, the reference obtained by `tcf_proto_create` is leaked because the error path jumps directly to `errout_tp` without releasing `tp_new`.
```
