# REAL BUG: drivers/mtd/nand/raw/loongson-nand-controller.c:878 loongson_nand_chip_init()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L879 | success     | YES | YES | ⚠️ Same premature put | success path returns 0; chip->flash_node still set, but no extra ref held. Driver remove will double-put. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L846 | error       | NO (before get) | N/A  | ✅ | nchips != 1, no node access |
| L850 | error       | NO (get returned NULL) | N/A  | ✅ | of_get_next_child returned NULL, no ref held |
| L860 | error       | YES (L847 of_get_next_child) | YES (L858 of_node_put) | ⚠️ Balanced locally but PREMATURE | chip->flash_node still points to node, but ref already released. Later cleanup (probe error, remove, or nand_release) will call of_node_put(chip->flash_node) → double put / refcount excess put. |
| L872 | error       | YES (L847 get) | YES (L858 put) | ⚠️ Same premature put | same as above |
| L876 | error       | YES | YES | ⚠️ Same premature put | mtd_device_register failed, nand_cleanup called, but node already put |
| L879 | success     | YES | YES | ⚠️ Same premature put | success path returns 0; chip->flash_node still set, but no extra ref held. Driver remove will double-put. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
of_get_next_child acquires a reference on the child node. The code immediately calls of_node_put(chip_np) after nand_set_flash_node, storing the pointer in chip->flash_node without retaining the reference. The NAND core's nand_cleanup does **not** release flash_node; the driver is responsible for keeping the reference until it explicitly puts it (typically in the remove function). This premature put will cause a refcount underflow (excess put) later when the driver's cleanup path eventually does another of_node_put(chip->flash_node).
```
