# REAL BUG: drivers/phy/mediatek/phy-mtk-xfi-tphy.c:328 mtk_xfi_tphy_reset()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

- The warning points to the return at L328, where the refcount has been improperly manipulated (excess put), consistent with the static analysis.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L328 | success     | YES (L325, `reset_control_deassert`) | YES (L323, `reset_control_assert`) | NO | PUT (assert) executed before any GET; if `deassert_count` is 0 on entry, the PUT causes an underflow/excess put before the later GET. The net get-put count is zero, but the ordering violates refcount invariants. |

## Analysis

- The function contains exactly one return path (L328).  
- On that path, `reset_control_assert()` (PUT) is called first, then `reset_control_deassert()` (GET).  
- The GET contract states `reset_control_deassert` increments `deassert_count`. The PUT contract states `reset_control_assert` decrements `deassert_count`.  
- The function assumes the reset was already deasserted (i.e., `deassert_count ≥ 1`) before the assert call. If `deassert_count == 0`, the assert is an **excess put**, producing a refcount underflow.  
- The later deassert does not retroactively fix the earlier underflow; the refcount state becomes invalid at the point of the assert.  
- No guard or check ensures `deassert_count > 0` before calling `reset_control_assert`.  
- The warning points to the return at L328, where the refcount has been improperly manipulated (excess put), consistent with the static analysis.

## PRE-VERDICT CHECKLIST

1. **“Held for device lifetime”?** – Not applicable; the function is a runtime reset, not a probe-only initialization.  
2. **“Ownership transferred”?** – No; no store to a long-lived structure, no documented cleanup.  
3. **Unconditional GET?** – `reset_control_deassert` is unconditional (always incs). The function calls it unconditionally, but the issue is the PUT without prior GET.  
4. **goto out between GET and PUT?** – No goto; the control flow is linear. The problem is the ordering: PUT first when the counter may be zero.

Because the PUT can be called while `deassert_count` is 0, and no prior GET exists in this function, the excess put is a real bug.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`mtk_xfi_tphy_reset()` unconditionally calls `reset_control_assert` before `reset_control_deassert`, causing an excess put on `deassert_count` when the reset line is not already deasserted.
```
