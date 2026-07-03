# REAL BUG: drivers/gpu/drm/i915/gt/intel_ring_submission.c:1454 intel_ring_submission_setup()

**Confidence**: HIGH | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

| L1436     | return 0             | N/A             | N/A                        | ✅             | shared ownership, no put required |

## Full Response

```
| Line      | Return Type         | GET Done? (ctx) | PUT Done? (ctx)           | Balanced?      | Notes |
|-----------|----------------------|-----------------|----------------------------|----------------|-------|
| L1375     | return -ENODEV       | N/A             | N/A                        | ✅             | before any ref |
| L1378 (goto err) | error path          | N/A             | N/A                        | ✅             | timeline is ERR, no gen7_wa_vma |
| L1388 (goto err_timeline) | error path        | N/A             | N/A                        | ✅             | ring ERR, no gen7_wa_vma |
| L1402 (goto err_ring) | error path          | N/A             | N/A                        | ✅             | gen7_wa_vma is ERR, no private ref |
| L1434 (goto err_gen7_put) | error path        | NO              | YES (`intel_context_put`)  | ❌ EXCESS PUT  | gen7_wa_vma is a shared engine resource; success path never releases it, so this put drops an unowned reference |
| L1436     | return 0             | N/A             | N/A                        | ✅             | shared ownership, no put required |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`gen7_wa_vma` is obtained from the engine’s long‑lived WA context; the function never acquires an additional reference to its private intel_context, yet the error path unconditionally calls `intel_context_put(gen7_wa_vma->private)`, causing an excess put on that kref.
```
