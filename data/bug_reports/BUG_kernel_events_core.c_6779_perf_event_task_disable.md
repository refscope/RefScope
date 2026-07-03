# REAL BUG: kernel/events/core.c:6779 perf_event_task_disable()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

mpty) | YES (but two puts per unlock) | ❌ EXCESS PUT           | For each event, `perf_event_ctx_unlock` does two put_ctx operations (contract →put_ctx(put),put_ctx(put)). If `perf_event_ctx_lock` gets only one reference, every iteration releases an extra reference, causing a refcount underflow. |

## Full Response

```
| Line | Return Type | GET Done?                  | PUT Done?                  | Balanced?               | Notes                                                                                                                                                                                                                                  |
|------|-------------|----------------------------|----------------------------|-------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| L6779 | success     | YES (if event list non‑empty) | YES (but two puts per unlock) | ❌ EXCESS PUT           | For each event, `perf_event_ctx_unlock` does two put_ctx operations (contract →put_ctx(put),put_ctx(put)). If `perf_event_ctx_lock` gets only one reference, every iteration releases an extra reference, causing a refcount underflow. |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`perf_event_ctx_unlock` unconditionally performs two puts on the context refcount (`put_ctx(put),put_ctx(put)`), while `perf_event_ctx_lock` likely acquires only a single reference. This imbalance leads to an excess put (refcount underflow) for every event processed, visible at the function return.
```
