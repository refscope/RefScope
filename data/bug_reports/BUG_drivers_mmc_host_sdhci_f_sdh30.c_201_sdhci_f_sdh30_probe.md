# REAL BUG: drivers/mmc/host/sdhci_f_sdh30.c:201 sdhci_f_sdh30_probe()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L191 | return 0    | YES | NO  | ⚠️  (held for device lifetime) | intended cross‑function balance with remove |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L124 | error       | NO  | N/A | ✅ | before any get |
| L134 | error       | NO  | N/A | ✅ | |
| L141 | error       | NO  | N/A | ✅ | |
| L145 | error       | NO  | N/A | ✅ | |
| L150 | goto err_clk | NO  | N/A | ✅ | err_clk label only unprepares clk_iface |
| L155 | goto err_clk | NO  | N/A | ✅ | |
| L160 | goto err_rst | NO  | N/A | ✅ | rst not obtained |
| L165 | goto err_rst | YES (unconditional contract) | NO  | ❌ LEAK | deassert returns error but still claims a ref; err_rst skips assert |
| L189 | goto err_add_host | YES | YES | ✅ | err_add_host calls reset_control_assert |
| L191 | return 0    | YES | NO  | ⚠️  (held for device lifetime) | intended cross‑function balance with remove |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`reset_control_deassert` unconditionally increments `deassert_count`, but the error path `goto err_rst` at L165 never calls `reset_control_assert`, leaking the reference.
```
