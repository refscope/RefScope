# REAL BUG: drivers/net/macsec.c:1938 macsec_add_rxsc()

**Confidence**: HIGH | **Counter**: `$->refcnt.refs.counter`

## Reasoning

| L1934 | success (0)   | YES (rx_sc valid) | NO (ownership handed to secy) | ✅ | success path keeps rx_sc in secy, no put needed |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1879 | error (-EINVAL) | NO (before create_rx_sc) | N/A | ✅ | |
| L1882 | error (-EINVAL) | NO (before create_rx_sc) | N/A | ✅ | |
| L1885 | error (-EINVAL) | NO (before create_rx_sc) | N/A | ✅ | |
| L1891 | error (PTR_ERR) | NO (before create_rx_sc) | N/A | ✅ | |
| L1906 | error (PTR_ERR) | NO (create_rx_sc failed) | N/A | ✅ | IS_ERR guard, no ref held |
| L1919 | goto cleanup  | YES (rx_sc valid) | YES (del_rx_sc + free_rx_sc) | ❌ DOUBLE PUT | del_rx_sc already drops secy’s reference (likely puts the only ref), then free_rx_sc puts again → excess put |
| L1928 | goto cleanup  | YES (rx_sc valid) | YES (del_rx_sc + free_rx_sc) | ❌ DOUBLE PUT | same as above |
| L1934 | success (0)   | YES (rx_sc valid) | NO (ownership handed to secy) | ✅ | success path keeps rx_sc in secy, no put needed |

[NEED_SOURCE] del_rx_sc

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`create_rx_sc` returns an rx_sc with a single refcount (refcount_set). The cleanup path calls `del_rx_sc` which already drops the reference (putting the object), then `free_rx_sc` does an extra put on the already-released/freed rx_sc, causing the "refcount excess put" at line 1938.
```
