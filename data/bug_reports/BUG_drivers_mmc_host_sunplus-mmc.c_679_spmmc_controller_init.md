# REAL BUG: drivers/mmc/host/sunplus-mmc.c:679 spmmc_controller_init()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L669 (assert returns zero) → L672 deassert → L679 | void | YES | YES | ✅ | Balanced assert‑deassert |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L669 (assert returns non‑zero) → implicit return at L679 | void | NO (deassert skipped) | YES (per contract) | ❌ | Excess put – put happens without matching get |
| L669 (assert returns zero) → L672 deassert → L679 | void | YES | YES | ✅ | Balanced assert‑deassert |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`reset_control_assert` always decrements per its contract, but if it fails (non‑zero return), the matching `reset_control_deassert` is skipped, leaving a net decrement (excess put).
```
