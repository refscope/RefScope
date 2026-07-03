# REAL BUG: drivers/spi/spi.c:2657 of_register_spi_device()

**Confidence**: LOW | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L? (spi_add_device succeeds)        | success (return spi)       | YES (by of_node_get) | NO                    | ❌ LEAK     | return without of_node_put; reference not released unless device release does it later (no evidence provided) |

## Full Response

```
```
| Line | Return Type      | GET Done? | PUT Done? | Balanced? | Notes |
|------|------------------|-----------|-----------|-----------|-------|
| L? (spi_alloc_device fails)         | error (goto err_out)       | NO (before get)        | N/A | ✅ | of_node_get not called |
| L? (of_alias_from_compatible fails) | error (goto err_out)       | NO (before get)        | N/A | ✅ | of_node_get not called |
| L? (of_spi_parse_dt fails)          | error (goto err_out)       | NO (before get)        | N/A | ✅ | of_node_get not called |
| L? (spi_add_device fails)           | error (goto err_of_node_put) | YES (by of_node_get) | YES (via of_node_put) | ✅ | explicit put before return |
| L? (spi_add_device succeeds)        | success (return spi)       | YES (by of_node_get) | NO                    | ❌ LEAK     | return without of_node_put; reference not released unless device release does it later (no evidence provided) |

VERDICT: REAL_BUG
CONFIDENCE: LOW

Success return path acquires a ref with `of_node_get` but never calls `of_node_put`. No ownership transfer with documented cleanup is visible; the device’s eventual release might (or might not) handle it, so by default the path leaks.
```
```
