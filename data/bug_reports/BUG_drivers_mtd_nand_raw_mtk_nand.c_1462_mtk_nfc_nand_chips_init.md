# REAL BUG: drivers/mtd/nand/raw/mtk_nand.c:1462 mtk_nfc_nand_chips_init()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

e get per child by `of_get_next_child`) | scoped cleanup: one put per child; **extra put** suspected inside callee → underflow | ❌ Excess (underflow) | **Warning line** – refcount excess put detected at this return. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1458 | error       | (per‑iteration GET/PUT balanced by scoped macro; auto‑release on return) | – | likely OK | Warning not associated with this path. |
| L1462 | success     | (scoped loop: one get per child by `of_get_next_child`) | scoped cleanup: one put per child; **extra put** suspected inside callee → underflow | ❌ Excess (underflow) | **Warning line** – refcount excess put detected at this return. |

[NEED_SOURCE] mtk_nfc_nand_chip_init  
[NEED_SOURCE] mtk_nfc_nand_chips_cleanup

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`for_each_child_of_node_scoped` auto‑releases the child node after each iteration, but `mtk_nfc_nand_chip_init` likely also calls `of_node_put` on the same child (without an additional get), causing a double put and refcount underflow on the success return at line 1462.
```
