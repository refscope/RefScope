# REAL BUG: drivers/net/ethernet/sfc/falcon/nic.c:143 ef4_nic_init_interrupt()

**Confidence**: HIGH | **Counter**: `$->refcount.refcount.refs.counter`

## Reasoning

| L123 | return 0      | YES (multiple adds) | FUTURE (held for later device‑lifetime cleanup) | ✅ | Success path – rmap stored in net_dev, cleaned up later in remove/fini |

## Full Response

```
| Line | Return Type   | GET Done? | PUT Done? | Balanced? | Notes |
|------|---------------|-----------|-----------|-----------|-------|
| L83  | goto fail1    | NO (no GET in this path) | N/A | ✅ | Non-MSI error path – no cpu_rmap involved |
| L86  | return 0      | NO (no GET) | N/A | ✅ | Non-MSI success – no cpu_rmap |
| L96  | goto fail1    | NO (alloc_irq_cpu_rmap failed) | N/A | ✅ | alloc_irq_cpu_rmap returned NULL – no cpu_rmap created |
| L107 | goto fail2    | YES (if any prior irq_cpu_rmap_add succeeded) | PARTIAL | ❌ LEAK (when ≥1 add succeeded) | free_irq_cpu_rmap does only **one** cpu_rmap_put; extra references from successful adds are never released |
| L119 | goto fail2    | YES (irq_cpu_rmap_add unconditional GET) | NO (only one cpu_rmap_put via free_irq_cpu_rmap, but refcount incremented by this add) | ❌ LEAK | irq_cpu_rmap_add always calls cpu_rmap_get even on failure; the single put in fail2 is insufficient |
| L123 | return 0      | YES (multiple adds) | FUTURE (held for later device‑lifetime cleanup) | ✅ | Success path – rmap stored in net_dev, cleaned up later in remove/fini |

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  
`irq_cpu_rmap_add` unconditionally increments the cpu_rmap refcount (contract says **unconditional GET**). On the error path at line L119 (`irq_cpu_rmap_add` fails) the function jumps to `fail2` where only `free_irq_cpu_rmap` is called, performing **one** `cpu_rmap_put`. The current add’s reference is never released, and any previously added references are also leaked (the single put is insufficient). The error path inside the loop must explicitly `cpu_rmap_put` for each association before freeing.
```
