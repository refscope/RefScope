# REAL BUG: drivers/nvme/target/fc.c:832 nvmet_fc_alloc_target_queue()

**Confidence**: HIGH | **Counter**: `$->ref.refs.counter`

## Reasoning

| L824 | return queue (success) | YES (kref_init) | deferred (ownership stored) | ✅ | Queue stored in assoc->queues[qid]; reference held for later removal |

## Full Response

```
| Line | Return Type | GET (queue->ref)? | PUT (queue->ref)? | Balanced? | Notes |
|------|-------------|-------------------|-------------------|-----------|-------|
| L789 | return NULL (bad qid) | NO (before alloc) | N/A | ✅ | |
| L793 | return NULL (alloc fail) | NO (before init) | N/A | ✅ | |
| L799 | goto out_free_queue (workqueue fail) | NO (kref_init not yet called) | N/A | ✅ | Falls through to kfree() at L831 |
| L819 | goto out_fail_iodlist (nvmet_sq_init fail) | **YES** (kref_init at L812) | **NO** | ❌ LEAK | kfree() done at L831 without kref_put; nvme_cq ref is properly put |
| L824 | return queue (success) | YES (kref_init) | deferred (ownership stored) | ✅ | Queue stored in assoc->queues[qid]; reference held for later removal |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Missing kref_put(&queue->ref) on the error path when nvmet_sq_init() fails at L819; the initial reference from kref_init() is leaked because the queue is freed directly without releasing that reference.
```
