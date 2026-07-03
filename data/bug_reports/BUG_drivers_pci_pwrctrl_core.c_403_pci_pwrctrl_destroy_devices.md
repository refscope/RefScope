# REAL BUG: drivers/pci/pwrctrl/core.c:403 pci_pwrctrl_destroy_devices()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

cenario where this would be a false positive is if `pci_pwrctrl_destroy_device` **does not** call `of_node_put` (or equivalent) – but that would contradict typical driver patterns and the semantics of “destroy” functions. Given the warning, the most likely conclusion is a real double‑put bug.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L403 | void return (end of function) | YES (via `of_get_next_available_child` in loop) | YES (scoped cleanup `of_node_put`) + **likely extra PUT** inside `pci_pwrctrl_destroy_device()` | **NO** (excess put) | Smatch reports “excess put” at this line; the double decrement would happen if `pci_pwrctrl_destroy_device()` also releases its reference to `child`. The scoped macro’s cleanup adds one put; an additional put inside the callee would leave the refcount underflowed. |

🔴 **Request for callee source needed to confirm**:  
`[NEED_SOURCE] pci_pwrctrl_destroy_device`  
`[NEED_SOURCE] for_each_available_child_of_node_scoped`

---

**Analysis**  
- The function loops over child nodes with `for_each_available_child_of_node_scoped(np, child)`.  
  This macro:
  - obtains each child via `of_get_next_available_child()`, which returns a node with a **reference taken** (unconditional GET on success, i.e., non‑NULL child).
  - uses a scoped cleanup (likely `__free(device_node)`) that calls `of_node_put(child)` at the **end of the scope** – i.e., after the function body exits. That is one PUT per iteration.
- `pci_pwrctrl_destroy_device(child)` is called inside the loop. By convention (and the function name), it is expected to **release** the device node reference it was given (another PUT). If it indeed calls `of_node_put(child)`, then the total number of PUTs per child equals 2, while the number of GETs equals 1 → **excess put** at the function exit (the scoped put fires after the last iteration). Smatch correctly reports that at line 403 the refcount is being decremented without a matching get.
- Even if the scoped cleanup only fires once at the end of the `for` loop (C99 variable scope), the double-put condition still holds: the callee would drop the reference first, and then the cleanup drops it again, hitting a zero‑underflow.

The only scenario where this would be a false positive is if `pci_pwrctrl_destroy_device` **does not** call `of_node_put` (or equivalent) – but that would contradict typical driver patterns and the semantics of “destroy” functions. Given the warning, the most likely conclusion is a real double‑put bug.

---

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
`pci_pwrctrl_destroy_device` almost certainly drops the child’s reference inside, leading to two `of_node_put` calls for one `of_get_next_available_child`; the scoped cleanup at line 403 then triggers the excess put detected by smatch. A full `[NEED_SOURCE]` of the callee is required to eliminate the remaining uncertainty.
```
