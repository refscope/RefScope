# REAL BUG: drivers/gpu/drm/sun4i/sun8i_tcon_top.c:234 sun8i_tcon_top_bind()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| L~234 | return 0 (success bind)| YES (intentional hold) | NO (released in unbind) | ✅ (bind lifespan) | bind success leaves deassert held; no local balance needed, leased for device lifetime    |

## Full Response

```
| Line  | Return Type            | GET Done?         | PUT Done?              | Balanced? | Notes                                                                                     |
|-------|------------------------|-------------------|------------------------|-----------|-------------------------------------------------------------------------------------------|
| L134  | return -ENOMEM         | NO (before deassert) | N/A                    | ✅         | early allocation failure                                                                  |
| L138  | return -ENOMEM         | NO (before deassert) | N/A                    | ✅         | clk_data alloc failure                                                                    |
| L147  | return PTR_ERR(rst)    | NO (before deassert) | N/A                    | ✅         | reset control get failure                                                                 |
| L153  | return PTR_ERR(bus)    | NO (before deassert) | N/A                    | ✅         | bus clock get failure                                                                     |
| L159  | return PTR_ERR(regs)   | NO (before deassert) | N/A                    | ✅         | ioremap failure                                                                           |
| L164  | return ret             | YES (deassert called, counter incremented unconditionally) | NO                     | ❌ LEAK    | deassert error path; reset_control_assert missing                                         |
| L170  | goto err_assert_reset  | YES                | YES (via assert at label) | ✅         | clk enable failure; assert called in cleanup                                              |
| L~?   | goto err_unregister_gates → err_assert_reset | YES | YES (via assert) | ✅         | gate/provider error paths; assert called after unregister and clk disable                 |
| L~234 | return 0 (success bind)| YES (intentional hold) | NO (released in unbind) | ✅ (bind lifespan) | bind success leaves deassert held; no local balance needed, leased for device lifetime    |

**PRE-VERDICT CHECKLIST**  
- **Held for device lifetime?** Applies only to the success return. The deassert error path (L164) is an early probe error where the device is not bound; `remove()`/`unbind` never fires → MUST explicitly release. **Leak confirmed.**  
- **Ownership transferred?** No ownership transfer inside this function.  
- **Unconditional GET?** `reset_control_deassert()` increments the internal `deassert_count` unconditionally (even on failure), as per contract and kernel implementation for shared resets. **Leak confirmed.**  
- **goto between GET and PUT?** The deassert error path uses a direct `return`, bypassing the `err_assert_reset` label that contains the required `reset_control_assert()`. **Leak confirmed.**

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`reset_control_deassert()` unconditionally increments the deassert reference counter. On the error path at L164 (deass
```
