# REAL BUG: drivers/pci/controller/dwc/pci-dra7xx.c:859 dra7xx_pcie_probe()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| final `return ret` (after `err_link` cleanup) | error cleanup | NO (already freed) | YES | ✅ | |

## Full Response

```
| Path Description | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------------------|-------------|-----------|-----------|-----------|-------|
| early returns before for loop (data, alloc, clk, etc.) | error | NO | N/A | ✅ | No `device_link_add` called |
| `IS_ERR(phy[i])` return (`i==0`) | error | NO | N/A | ✅ | No prior links |
| `IS_ERR(phy[i])` return (`i>0`) | error | YES (`i` links) | NO | ❌ **LEAK** | `device_link_add` succeeded for earlier phy devices; no `device_link_del` |
| `!link[i]` → `goto err_link` | error cleanup | YES (previous links) | YES (`err_link` calls `device_link_del`) | ✅ | |
| `dra7xx_pcie_enable_phy()` failure → `return ret` | error | YES (all links) | NO | ❌ **LEAK** | All `phy_count` links added; function returns without cleanup |
| `pm_runtime_get_sync` fail → `goto err_get_sync` | error cleanup | YES | YES (falls through to `err_link`) | ✅ | |
| `goto err_gpio` (gpio error / switch errors) | error cleanup | YES | YES (falls through to `err_link`) | ✅ | |
| `goto err_deinit` (irq failure) | error cleanup | YES | YES (falls through to `err_gpio` → `err_link`) | ✅ | |
| success `return 0` | success | YES | NO (held for lifetime) | ✅ | Device links kept for device lifetime; remove path releases later |
| final `return ret` (after `err_link` cleanup) | error cleanup | NO (already freed) | YES | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`device_link_add` references leaked on two paths: (1) early `return PTR_ERR(phy[i])` inside the for‑loop when a later phy get fails but earlier device links were already created, and (2) `return ret` after `dra7xx_pcie_enable_phy` failure without calling `device_link_del` on all successfully added links.
```
