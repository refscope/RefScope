# REAL BUG: drivers/infiniband/hw/hfi1/user_sdma.c:565 hfi1_user_sdma_process_request()

**Confidence**: HIGH | **Counter**: `pq->n_reqs.counter`

## Reasoning

(copy, opcode, vl, pkey, GRH, iovs, ntids, sde, while loop) | error | YES | YES (npkts > 0 always) | ✅ | after `!npkts` check, so condition true → `pq_update` called |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L308 | error | NO | N/A | ✅ | before `atomic_inc` |
| L312 | error | NO | N/A | ✅ | before `atomic_inc` |
| L320 | error | NO | N/A | ✅ | before `atomic_inc` |
| L331 | error | NO | N/A | ✅ | before `atomic_inc` |
| L342 | error | NO | N/A | ✅ | before `atomic_inc` |
| L348 | error | NO | N/A | ✅ | before `atomic_inc` |
| ~L369 (`goto free_req` from EXPECTED block) | error | YES | Conditional: YES only if `npkts>0` | ❌ LEAK when `npkts==0` | `free_req` skips `pq_update(pq)` if `seqsubmitted (0) < npkts` is false |
| ~L375 (`goto free_req` on `!info.npkts \|\| req->data_iovs > MAX`) | error | YES | NO if `!npkts`, YES if vectors too many | ❌ LEAK when `npkts==0` | explicit `npkts==0` path, condition false, no put |
| L380+ subsequent gotos (copy, opcode, vl, pkey, GRH, iovs, ntids, sde, while loop) | error | YES | YES (npkts > 0 always) | ✅ | after `!npkts` check, so condition true → `pq_update` called |
| L448 (success) | success | YES | NO (deferred) | ✅ (ownership to completion) | completion callback eventually handles release |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`atomic_inc` is unconditional, but error path when `npkts == 0` skips `pq_update` (the condition `seqsubmitted < npkts` is false), leaking the reference.
```
