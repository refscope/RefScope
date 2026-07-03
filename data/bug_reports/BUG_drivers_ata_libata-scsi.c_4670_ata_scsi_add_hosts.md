# REAL BUG: drivers/ata/libata-scsi.c:4670 ata_scsi_add_hosts()

**Confidence**: MEDIUM | **Counter**: `$->tagset_refcnt.refcount.refs.counter`

## Reasoning

| L4661 (scsi_add_host_with_dma fails, goto err_alloc) → L4669 while loop | error path: removes previously added hosts (skips the failed one) | For removed hosts: NO (no get) | For removed hosts: YES (put via scsi_remove_host) | ❌ EXCESS PUT | Same excess put for each successfully added host. |

## Full Response

```
| Line | Return Type | GET Done? (tagset_refcnt) | PUT Done? (tagset_refcnt, via scsi_remove_host) | Balanced? | Notes |
|------|-------------|---------------------------|--------------------------------------------------|-----------|-------|
| L4664 (return 0) | success (no ports failed) | NO (no get on tagset) | NO (no remove) | ✅ not relevant | No put issued; no excess. |
| L4648 (shost alloc fails, goto err_alloc) → L4669 while loop | error path: removes previously added hosts | For each removed shost: NO (scsi_add_host_with_dma contract does **not** include tagset_refcnt get) | For each removed shost: YES (scsi_remove_host does a kref_put on tagset_refcnt) | ❌ EXCESS PUT | Every scsi_remove_host call here triggers an unmatched put on tagset_refcnt. |
| L4661 (scsi_add_host_with_dma fails, goto err_alloc) → L4669 while loop | error path: removes previously added hosts (skips the failed one) | For removed hosts: NO (no get) | For removed hosts: YES (put via scsi_remove_host) | ❌ EXCESS PUT | Same excess put for each successfully added host. |

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  

The contract for `scsi_add_host_with_dma` does **not** list a get on `$->tagset_refcnt`, so no matching acquisition exists for the put that `scsi_remove_host` performs on that counter. Every error path that removes successfully added hosts therefore triggers an excess put, as reported by the static analysis. (If a hidden get exists inside `scsi_add_host_with_dma` that the contract missed, this would be a false positive; under contract-driven rules it is treated as a real imbalance.)
```
