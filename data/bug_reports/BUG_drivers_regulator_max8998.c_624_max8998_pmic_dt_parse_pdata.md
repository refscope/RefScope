# REAL BUG: drivers/regulator/max8998.c:624 max8998_pmic_dt_parse_pdata()

**Confidence**: HIGH | **Counter**: `reg_np->kobj.kref.refcount.refs.counter`

## Reasoning

- goto out / label issues? Not present.

## Full Response

```
```
| Line | Return Type | GET Done? (reg_np) | PUT Done? (L585) | Balanced? | Notes |
|------|-------------|--------------------|------------------|-----------|-------|
| L555 | error (-EINVAL) | NO (before loop) | N/A | ✅ | |
| L566 | error (-ENOMEM) | NO (before loop) | N/A | ✅ | |
| L612 | error (-EINVAL) | YES, if loop found a child on last iteration | YES (L585 executed) | ⚠️ FUNCTION-BALANCE OK, BUT OWNERSHIP VIOLATION | reg_np reference was stored in rdata->reg_node; L585 should not put it. The rdata will release it later → double put |
| L621 | error (-EINVAL) | same as L612 | YES (L585 executed) | ⚠️ SAME VIOLATION | |
| L624 | success (0)     | same as L612 | YES (L585 executed) | ⚠️ SAME VIOLATION | |

**Pre-Verdict Checklist**:
- "Held for device lifetime"? No.
- "Ownership transferred"? The reference is explicitly stored in rdata->reg_node, yet the function still calls of_node_put() on the same node after the loop. This is a classic ownerhsip-handoff failure: the put releases the reference that should have been kept by the owner.
- Unconditional GET? No, but the GET does happen on the affected path.
- goto out / label issues? Not present.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
of_get_child_by_name() acquires a reference, which is stored in rdata->reg_node (ownership transferred). The subsequent of_node_put(reg_np) at L585 incorrectly releases that same reference, leaving rdata->reg_node with a dangling pointer and causing a double-put when the rdata array is later cleaned up.
```
```
