# REAL BUG: drivers/gpu/drm/nouveau/nvkm/engine/fifo/ucgrp.c:124 nvkm_ucgrp_new()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| error path | YES (`kref_init` via `nvkm_object_ctor`) | NO (no `nvkm_object_del`/`kref_put`) | ❌ LEAK   | `ucgrp` allocated and initialized but not released |

## Full Response

```
| Line | Return Type | GET Done? (ucgrp kref) | PUT Done? (ucgrp kref) | Balanced? | Notes |
|------|-------------|-----------------------|------------------------|-----------|-------|
| L90  | early return  | NO                    | N/A                    | ✅        | Before `ucgrp` allocation |
| L94  | early return  | NO                    | N/A                    | ✅        | Before `ucgrp` allocation |
| L99  | early return  | NO                    | N/A                    | ✅        | Before `ucgrp` allocation |
| L103 | early return  | NO                    | N/A                    | ✅        | `vmm` error, no `ucgrp` |
| L108 (goto done) | error path | NO (allocation failed) | N/A                    | ✅        | `ucgrp` is NULL, no kref |
| L116 (goto done) | error path | YES (`kref_init` via `nvkm_object_ctor`) | NO (no `nvkm_object_del`/`kref_put`) | ❌ LEAK   | `ucgrp` allocated and initialized but not released |
| L120‑123 (fall‑through) | success | YES (ownership passed) | N/A (caller releases)  | ✅        | `*pobject` set, caller will clean up |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

`nvkm_object_ctor()` initializes an embedded kref on `ucgrp`. When `nvkm_cgrp_new()` fails at line 116, the function jumps to `done`, releases only `vmm`, and returns an error **without releasing the `ucgrp` object** — the caller never sees the object, causing a refcount leak.
```
