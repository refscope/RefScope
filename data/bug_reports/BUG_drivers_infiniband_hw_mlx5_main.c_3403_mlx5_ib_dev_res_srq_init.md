# REAL BUG: drivers/infiniband/hw/mlx5/main.c:3403 mlx5_ib_dev_res_srq_init()

**Confidence**: HIGH | **Counter**: `$->ext.cq->usecnt.counter`

## Reasoning

nit succeeded) | NO (s0 destroyed, but CQ init ref remains) | ❌ LEAK | ib_destroy_srq(s0) releases s0’s CQ ref, but CQ init ref still held |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L3356 (return 0) | early success | NO (no get yet) | N/A | ✅ | before mlx5_ib_dev_res_cq_init |
| L3359 (goto unlock) | s1 already set | NO (no get yet) | N/A | ✅ | avoids CQ init, safe |
| L3362 (goto unlock) | CQ init failed | NO (CQ init failed, assumed clean) | N/A | ✅ | mlx5_ib_dev_res_cq_init should rollback on failure |
| L3374 (goto unlock) | s0 creation failed | YES (CQ init succeeded) | NO | ❌ LEAK | CQ init ref not released, no ib_destroy_srq (s0 invalid) |
| L3389 (goto unlock) | s1 creation failed | YES (CQ init succeeded) | NO (s0 destroyed, but CQ init ref remains) | ❌ LEAK | ib_destroy_srq(s0) releases s0’s CQ ref, but CQ init ref still held |
| L3393 (fallthrough unlock) | success | YES | YES (refs stored in devr, cleaned on device unload) | ✅ | CQ ref held for device lifetime, correctly managed |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`mlx5_ib_dev_res_cq_init` acquires a reference on the CQ (stored in devr->c0). On the error paths after it succeeds (s0 or s1 failure), the function returns without releasing that CQ reference, and no later cleanup undoes the CQ initialization, causing a permanent refcount leak.
```
