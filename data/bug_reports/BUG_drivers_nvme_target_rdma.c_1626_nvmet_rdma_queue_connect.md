# REAL BUG: drivers/nvme/target/rdma.c:1626 nvmet_rdma_queue_connect()

**Confidence**: HIGH | **Counter**: `$->nvme_cq.ref.refs.counter`

## Reasoning

| L1645 (success, list add) | `return 0` | YES | ownership transferred (list) | ✅ | Queue inserted into `nvmet_rdma_queue_list`, freed on disconnect |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1582 (no ndev) | `return -ECONNREFUSED` | NO (before alloc) | N/A | ✅ | No queue allocated |
| L1589 (queue alloc fails) | `goto put_device` / `return -ENOMEM` | NO (alloc returned NULL) | N/A | ✅ | `queue` is NULL |
| L1626 (pending > NVMET_RDMA_BACKLOG) | `return NVME_SC_CONNECT_CTRL_BUSY` | YES | NO | ❌ LEAK | Queue allocated, direct return skips `free_queue` |
| L1636 (cm_accept fails) | `goto free_queue` / `return ret` | YES | YES | ✅ | `free_queue` calls `nvmet_rdma_free_queue` |
| L1645 (success, list add) | `return 0` | YES | ownership transferred (list) | ✅ | Queue inserted into `nvmet_rdma_queue_list`, freed on disconnect |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`nvmet_rdma_alloc_queue` at L1588 succeeded; at L1626 `return NVME_SC_CONNECT_CTRL_BUSY` returns without `nvmet_rdma_free_queue`, leaking the queue reference.
```
