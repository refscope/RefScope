# REAL BUG: net/sched/sch_generic.c:332 dequeue_skb()

**Confidence**: HIGH | **Counter**: `$->cpu_qstats->qlen`

## Reasoning

| L317→L327 (no skb) | bad_txq returns NULL, dequeue returns NULL, trace, return NULL | No | ✅ | |

## Full Response

```
[NEED_SOURCE] try_bulk_dequeue_skb_slow
[NEED_SOURCE] qdisc_dequeue_skb_bad_txq

| Line | Path Description | Dec (PUT) on cpu_qstats->qlen? | Balanced? | Notes |
|------|------------------|--------------------------------|-----------|-------|
| L308 | gso_skb empty → validate → ONETXQUEUE frozen → return NULL | No | ✅ | no dec needed |
| L314 | qdisc_dequeue_skb_bad_txq returns SKB_XOFF_MAGIC → return NULL | No | ✅ | |
| L300→L327 | gso_skb peek, txq frozen/stopped, skb=NULL, clear missed, trace → return NULL | No | ✅ | |
| L289→L327 | gso_skb dequeue, qdisc_is_percpu_stats → qdisc_qstats_cpu_qlen_dec, trace, return skb | Yes (gso dec) | ✅ | dec corresponds to skb enqueued into gso_skb |
| L311→L315→L319→L323→L327 | qdisc_dequeue_skb_bad_txq returns real skb, goto bulk, try_bulk_dequeue_skb_slow (assumed to dec cpu_qstats->qlen), trace, return skb | **Yes (bulk dec)** | **❌ EXCESS** | skb was already dequeued and its qlen dec’d earlier; this second dec drives the refcount below zero → refcount excess put |
| L317→L318→L319→L323→L327 | q->dequeue returns skb, bulk, try_bulk_dequeue_skb_slow dec, trace, return skb | Yes (bulk dec) | ✅ | normal dequeue path, one dec per skb |
| L317→L327 (no skb) | bad_txq returns NULL, dequeue returns NULL, trace, return NULL | No | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The refcount excess put on cpu_qstats->qlen occurs because dequeue_skb retrieves a previously dequeued skb via qdisc_dequeue_skb_bad_txq and then calls try_bulk_dequeue_skb_slow, which decrements the already-zero qlen counter a second time.
```
