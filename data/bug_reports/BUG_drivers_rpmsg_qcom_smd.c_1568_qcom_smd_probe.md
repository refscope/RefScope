# REAL BUG: drivers/rpmsg/qcom_smd.c:1568 qcom_smd_probe()

**Confidence**: LOW | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

at loop exit. If the edge function also puts the node, that double‑free would manifest as an excess put. Because I cannot verify the macro’s internal behaviour, I classify this as **REAL_BUG** with low confidence based on the warning’s implication of a put without matching get at the return point.

## Full Response

```
[NEED_SOURCE] for_each_available_child_of_node
[NEED_SOURCE] qcom_smd_register_edge

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1563 | error       | NO (before loop) | N/A  | ✅ | qcom_smem check, no node ref |
| L1568 | success     | Depends on macro | Depends on macro | ❓ | warning suggests extra put, macro may include internal put plus possible put from edge function |

Without the macro definition and the edge function source, I cannot determine the exact reference lifetime. The warning line 1568 is just `return 0;`, but the excess put may originate from the `for_each_available_child_of_node` macro’s cleanup (if it now releases the last child reference) combined with a reference consumption or an additional put inside `qcom_smd_register_edge`. In standard kernels the macro traditionally leaks, but a new version may put the node at loop exit. If the edge function also puts the node, that double‑free would manifest as an excess put. Because I cannot verify the macro’s internal behaviour, I classify this as **REAL_BUG** with low confidence based on the warning’s implication of a put without matching get at the return point.

VERDICT: REAL_BUG
CONFIDENCE: LOW

--- [NEED_SOURCE r1] ---

[NEED_SOURCE] for_each_available_child_of_node from include/linux/of.h
[NEED_SOURCE] qcom_smd_register_edge - actual implementation (likely in drivers/soc/qcom/smd.c or similar)

--- [NEED_SOURCE r2] ---

[NEED_SOURCE]

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1563 | error       | NO (before loop) | N/A  | ✅ | qcom_smem check, no node ref |
| L1568 | success     | Unknown (depends on macro and callee) | Unknown | ❓ | warning suggests extra put; macro or edge function may introduce unbalanced put |

The actual implementation of `qcom_smd_register_edge` and the `for_each_available_child_of_node` macro remain unavailable after multiple requests. Without them, the reference‑counting contract cannot be verified. The warning points to an EXCESS put on `node` at L1568 (`return 0;`), which implies a put with no matching get on the success path. In the absence of counter‑evidence, this is likely a real bug.

VERDICT: REAL_BUG
CONFIDENCE: LOW
Excess put on `node` at L1568 suggested by warning; missing sources for `for_each_available_child_of_node` and `qcom_smd_register_edge` prevent definitive contract verification, but the imbalance is consistent with a refcount leak.
```
