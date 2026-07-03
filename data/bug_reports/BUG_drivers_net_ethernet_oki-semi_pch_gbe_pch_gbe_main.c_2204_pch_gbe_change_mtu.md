# REAL BUG: drivers/net/ethernet/oki-semi/pch_gbe/pch_gbe_main.c:2204 pch_gbe_change_mtu()

**Confidence**: HIGH | **Counter**: `$->irq_sem.counter`

## Reasoning

| L2190 → L2191 | error (err) after pch_gbe_up failure | YES (pch_gbe_down called) | ⚠️? (second pch_gbe_up called but return not checked; if it fails, sem NOT released) | ❌ LEAK | Error recovery tries pch_gbe_up again without checking result; sem leak if second up fails. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2193 | success (0) | NO (netif_running false, pch_gbe_down skipped) | N/A | ✅ | Device not running, no down/up needed. |
| L2191 → L2205 | success (0) when pch_gbe_up succeeds | YES (pch_gbe_down called) | YES (pch_gbe_up succeeded, likely releases sem) | ✅ | Normal MTU change while running. |
| L2190 → L2191 | error (err) after pch_gbe_up failure | YES (pch_gbe_down called) | ⚠️? (second pch_gbe_up called but return not checked; if it fails, sem NOT released) | ❌ LEAK | Error recovery tries pch_gbe_up again without checking result; sem leak if second up fails. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
pch_gbe_down acquires irq_sem; error path calls pch_gbe_up again without checking its return, risking permanent semaphore leak if second up also fails.
```
