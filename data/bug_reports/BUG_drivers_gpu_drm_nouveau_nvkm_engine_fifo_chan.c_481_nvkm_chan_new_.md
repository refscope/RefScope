# REAL BUG: drivers/gpu/drm/nouveau/nvkm/engine/fifo/chan.c:481 nvkm_chan_new_()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

- The warning at line 481 (`inconsistent refcounting` on `$->kref.refcount.refs.counter`) flags the mismatch between the success path (where the ref is eventually released by the caller) and the numerous error paths where it is **permanently leaked**.

## Full Response

```
| Line | Return Type | GET Done? (cgrp) | Additional GETs (vmm/memory) | PUT Done? | Balanced? | Notes |
|------|-------------|------------------|-----------------------------|-----------|-----------|-------|
| L365 (args)       | -EINVAL     | NO               | none                        | N/A       | ✅ | Before any reference acquisition |
| L369 (alloc)      | -ENOMEM     | NO               | none                        | N/A       | ✅ | kzalloc failed, no cgrp |
| L387 (cgrp_new fail) | ret | NO (get failed)  | none                        | N/A       | ✅ | cgrp_new fails → no reference taken (conditional success) |
| L394 (cgrp mismatch) | -EINVAL | NO               | none                        | N/A       | ✅ | Before nvkm_cgrp_ref call |
| L402 (gpuobj fail)   | ret      | YES              | none (vmm not taken)        | NO        | ❌ LEAK | cgrp ref leaked |
| L406 (vmm WARN)      | -EINVAL   | YES              | none (before vmm_ref)       | NO        | ❌ LEAK | cgrp ref leaked |
| L409 (vmm_join fail) | ret      | YES              | none (before vmm_ref)       | NO        | ❌ LEAK | cgrp ref leaked |
| L413 (object_bind fail) | ret  | YES              | vmm=YES if vmm path         | NO        | ❌ LEAK | cgrp leak + vmm leak if applicable |
| L418 (ouserd check)  | -EINVAL   | YES              | vmm=YES                     | NO        | ❌ LEAK | cgrp + vmm leak |
| L422 (mem kmap fail) | ret      | YES              | vmm=YES                     | NO        | ❌ LEAK | cgrp + vmm leak |
| L427 (chan->id <0)   | -ENOSPC   | YES              | vmm=YES, memory=NO*         | NO        | ❌ LEAK | cgrp + vmm leak; memory ref not taken unless bar path entered |
| L432 (ramfc write fail) | ret  | YES              | vmm=YES, memory depends     | NO        | ❌ LEAK | cgrp + vmm (+ optional memory) leak |
| L481 (success)       | 0          | YES              | vmm/memory as taken         | (caller)  | ✅ | Ownership transferred via *pchan; caller responsible for cleanup |

**Notes:**

- **cgrp reference** acquired unconditionally via `nvkm_cgrp_new` (success) or `nvkm_cgrp_ref` (both **UNCONDITIONAL** for the taken reference).  
- All error paths after that acquisition return without calling `nvkm_cgrp_unref` (or equivalent `kref_put`).  
- No ownership transfer to any persistent structure on error paths; the channel is not stored anywhere that would later release the references.  
- The warning at line 481 (`inconsistent refcounting` on `$->kref.refcount.refs.counter`) flags the mismatch between the success path (where the ref is eventually released by the caller) and the numerous error paths where it is **permanently leaked**.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
Every error return after `nvkm_cgrp_new` success or `nvkm_cgrp_ref` leaks the cgrp (and often vmm/memory) reference because no `kref_put`/`nvkm_cgrp_unref` is called on those paths.
```
