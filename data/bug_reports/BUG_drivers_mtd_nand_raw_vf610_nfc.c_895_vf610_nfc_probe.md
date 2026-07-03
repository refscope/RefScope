# REAL BUG: drivers/mtd/nand/raw/vf610_nfc.c:895 vf610_nfc_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L853 | return 0 (success) | NO | NO | ⚠️ (excess put later) | dangling pointer; excess put triggered in remove() |

## Full Response

```
| Line | Return Type | GET Done? (chip holds ref) | PUT Done? (chip releases) | Balanced? | Notes |
|------|-------------|---------------------------|--------------------------|-----------|-------|
| L812 | error (devm_kzalloc) | N/A | N/A | ✅ | before loop |
| L817 | error (platform_get_irq) | N/A | N/A | ✅ | |
| L821 | error (ioremap) | N/A | N/A | ✅ | |
| L826 | error (clk) | N/A | N/A | ✅ | |
| L830 | error (match_data) | N/A | N/A | ✅ | |
| L835 | error (duplicate chip) | NO (flash node not set) | NO | ✅ | scoped cleanup releases iter ref |
| L840 | error (no chip) | NO | NO | ✅ | |
| L845 | error (devm_request_irq) | NO (chip never took ref) | NO | ⚠️ (no kref underflow) | dangling pointer, not yet excess put |
| L849 | error (nand_scan) | NO | NO | ⚠️ | same |
| L852 | goto err_cleanup_nand | NO (chip never got ref) | YES (via nand_cleanup) | ❌ EXCESS PUT | nand_cleanup calls of_node_put on child; refcount already 0 after scoped loop |
| L853 | return 0 (success) | NO | NO | ⚠️ (excess put later) | dangling pointer; excess put triggered in remove() |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`nand_set_flash_node` does not increment the child’s kref; the scoped loop `__free(device_node)` already drops the iterator’s reference when the loop statement ends. The `err_cleanup_nand` path then calls `nand_cleanup` → `of_node_put` on the same node, exceeding the reference.
```
