# REAL BUG: drivers/scsi/esas2r/esas2r_init.c:708 esas2r_resume()

**Confidence**: HIGH | **Counter**: `$->dis_ints_cnt.counter`

## Reasoning

| ~L695 (IRQ claimed, success) | success (falls to error_exit) | YES | YES (esas2r_enable_chip_interrupts) | ✅ | balanced on success |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L660 (if (!a) goto error_exit) | error | NO | N/A | ✅ | before disable |
| ~L665 (esas2r_map_regions fail) | error | NO | N/A | ✅ | before disable |
| ~L677 (!esas2r_power_up) goto error_exit | error | YES (esas2r_disable_chip_interrupts called) | NO | ❌ LEAK | enable missing on error path |
| ~L685 (IRQ not claimed, else goto) | error | YES | NO | ❌ LEAK | same get, no enable |
| ~L695 (IRQ claimed, success) | success (falls to error_exit) | YES | YES (esas2r_enable_chip_interrupts) | ✅ | balanced on success |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
esas2r_disable_chip_interrupts (GET) increments dis_ints_cnt; error paths (power_up fail, IRQ not claimed) skip esas2r_enable_chip_interrupts (PUT), leaking the counter.
```
