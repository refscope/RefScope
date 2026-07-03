# REAL BUG: drivers/regulator/s5m8767.c:626 s5m8767_pmic_dt_parse_pdata()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L584 (final `return 0`) | success | YES – all child refs stored | NO (ownership transferred to `pdata`; regulator core cleans up later) | ✅ (by design) | No bug on success path; references are held for the driver’s lifetime |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L494 | error (`-ENODEV`) | NO (before any child node acquisition) | N/A | ✅ | |
| L499 | error (`-EINVAL`) | NO (no child processed yet) | N/A | ✅ | `regulators_np` auto-released via `__free(device_node)` |
| L504 | error (`-ENOMEM`) | NO (no child processed yet) | N/A | ✅ | |
| L507 | error (`-ENOMEM`) | NO (no child processed yet) | N/A | ✅ | |
| L523 (inside loop, `IS_ERR` branch) | error (`PTR_ERR`) | YES – previous children’s refs already stored in `rdata->reg_node` | NO (only current child is put; previously stored refs remain) | ❌ LEAK | Missing `of_node_put` for earlier stored nodes |
| L543 (buck2 error) | error (`-EINVAL`) | YES – all child refs stored | NO | ❌ LEAK | All child node refs leaked after loop |
| L552 (buck3 error) | error (`-EINVAL`) | YES – all child refs stored | NO | ❌ LEAK | Same as above |
| L561 (buck4 error) | error (`-EINVAL`) | YES – all child refs stored | NO | ❌ LEAK | Same as above |
| L584 (final `return 0`) | success | YES – all child refs stored | NO (ownership transferred to `pdata`; regulator core cleans up later) | ✅ (by design) | No bug on success path; references are held for the driver’s lifetime |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

On error paths (L523, L543, L552, L561) the function stores device-node references acquired via `for_each_child_of_node` but never releases them before returning, leaking the refcount of those nodes.
```
