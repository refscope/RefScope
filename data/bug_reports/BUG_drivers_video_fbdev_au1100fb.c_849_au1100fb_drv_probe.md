# REAL BUG: drivers/video/fbdev/au1100fb.c:849 au1100fb_drv_probe()

**Confidence**: HIGH | **Counter**: `$->core.ref.refcount.refs.counter`

## Reasoning

| L815 | success (return 0) | YES | NO (intentional) | ✅ | Clk held for driver lifetime, released in remove() |

## Full Response

```
| Line | Return Type | GET Done? (clk_get success) | PUT Done? (clk_put) | Balanced? | Notes |
|------|-------------|-----------------------------|---------------------|-----------|-------|
| L736 | error (return -ENOMEM) | NO (before clk_get) | N/A | ✅ | |
| L739 | goto failed | NO (before clk_get) | N/A (failed label sees lcdclk=NULL) | ✅ | |
| L747 | error (return -EFAULT) | NO (before clk_get) | N/A | ✅ | |
| L760 | error (return -EBUSY) | NO (before clk_get) | N/A | ✅ | |
| L783 | error (return -ENOMEM) | YES | NO | ❌ LEAK | dmam_alloc_coherent fails after clk_get, no clk_put |
| L800 | error (return -ENOMEM) | YES | NO | ❌ LEAK | pseudo_palette alloc fails, no clk_put |
| L804 | error (return -EFAULT) | YES | NO | ❌ LEAK | fb_alloc_cmap fails, no clk_put |
| L812 | goto failed | YES | YES (via failed label) | ✅ | register_framebuffer fails, cleanup works |
| L815 | success (return 0) | YES | NO (intentional) | ✅ | Clk held for driver lifetime, released in remove() |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`clk_get` (conditional) succeeds at L768. Three early error returns (L783, L800, L804) do not call `clk_put` or `clk_disable_unprepare`, leaking the clock reference.
```
