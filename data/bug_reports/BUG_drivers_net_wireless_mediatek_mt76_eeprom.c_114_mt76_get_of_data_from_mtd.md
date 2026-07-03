# REAL BUG: drivers/net/wireless/mediatek/mt76/eeprom.c:114 mt76_get_of_data_from_mtd()

**Confidence**: HIGH | **Counter**: `$->refcnt.refcount.refs.counter`

## Reasoning

| subsequent gotos (ret error, retlen<len, devm_kstrdup fail) | goto out_put_node | YES (ref already released) | YES (already put) | ✅ | put_mtd_device already executed |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L48 (approx) | error return -ENOENT | NO (before get) | N/A | ✅ | early of_get_property fail |
| L52 (approx) | error return -ENOENT | NO (before get) | N/A | ✅ | phandle zero |
| L55 (approx) | error return -EINVAL | NO (before get) | N/A | ✅ | of_find_node_by_phandle fail |
| L64 (approx) | goto out_put_node (IS_ERR) | NO (get failed) | N/A | ✅ | IS_ERR guard, no ref held |
| **L78 (approx)** | **goto out_put_node (size check)** | **YES** | **NO** | **❌ LEAK** | **size <= sizeof(*list) after successful get_mtd_device_nm, no put** |
| L88–L90 (approx) | after mtd_read → put_mtd_device called | YES | YES | ✅ | puts ref immediately after read |
| subsequent gotos (ret error, retlen<len, devm_kstrdup fail) | goto out_put_node | YES (ref already released) | YES (already put) | ✅ | put_mtd_device already executed |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Early return on `if (size <= sizeof(*list))` after successful `get_mtd_device_nm()` skips `put_mtd_device()`, leaking the mtd refcount.
```
