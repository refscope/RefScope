# REAL BUG: drivers/infiniband/hw/mlx5/srq.c:316 mlx5_ib_create_srq()

**Confidence**: HIGH | **Counter**: `$->common.refcount.refs.counter`

## Reasoning

| ~300 | return 0 (success)   | YES | NO (ownership transfer) | ✅ | normal success, refcount held by subsystem |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~194 | return -EOPNOTSUPP   | NO (before get) | N/A | ✅ | srq_type check before any get |
| ~202 | return -EINVAL       | NO (before get) | N/A | ✅ | max_wr/max_sge sanity check |
| ~208 | return err           | NO (before get) | N/A | ✅ | mlx5_ib_dev_res_cq_init error |
| ~220 | return -EINVAL       | NO (before get) | N/A | ✅ | desc_size/max_gs check |
| ~225 | return -EINVAL       | NO (before get) | N/A | ✅ | desc_size < sizeof check |
| ~230 | return -EINVAL       | NO (before get) | N/A | ✅ | buf_size < desc_size check |
| ~238 | return err           | NO (before get) | N/A | ✅ | create_srq_user/kernel error |
| ~260 | goto err_usr_kern_srq| NO (before get) | N/A | ✅ | TM log_list_size check before mlx5_cmd_create_srq |
| ~280 | goto err_usr_kern_srq| **YES** (unconditional) | **NO**  | **❌ LEAK** | mlx5_cmd_create_srq failed; err_usr_kern_srq has no mlx5_cmd_destroy_srq |
| ~295 | goto err_core → err_usr_kern_srq | YES | YES | ✅ | udata copy failure; err_core does mlx5_cmd_destroy_srq |
| ~300 | return 0 (success)   | YES | NO (ownership transfer) | ✅ | normal success, refcount held by subsystem |

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  

**One-line reasoning:** `mlx5_cmd_create_srq()` unconditionally sets the refcount (contract says `→refcount_set(set)`), but the error path when it fails (goto `err_usr_kern_srq`) does **not** call the matching `mlx5_cmd_destroy_srq()`, leaking the reference.
```
