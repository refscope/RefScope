# REAL BUG: net/bluetooth/hci_conn.c:2478 hci_connect_cis()

**Confidence**: MEDIUM | **Counter**: `$->refcnt.counter`

## Reasoning

| ~2483 (return cis) | success | **NO** (per warning) | YES | ❌ Excess | Drop before returning; if bind gave no ref, the drop is excessive. Link may hold a ref, but that doesn’t justify this drop. |

## Full Response

```
| Line | Return Type | GET (cis) Done? | PUT (cis) Done? | Balanced? | Notes |
|------|-------------|-----------------|-----------------|-----------|-------|
| ~2448 (IS_ERR(le)) | error return (le) | N/A | N/A | N/A | No cis yet; le not obtained. |
| ~2470 (IS_ERR(cis)) | error return (cis) | NO (cis is ERR) | N/A | N/A | le dropped, no cis reference to drop. |
| ~2478 (hci_conn_drop(cis), then !link) | error return (ENOLINK) | **NO** (per warning) | YES | ❌ Excess | `hci_bind_cis` appears not to increment the refcount → drop is a double-put / premature put. |
| ~2483 (return cis) | success | **NO** (per warning) | YES | ❌ Excess | Drop before returning; if bind gave no ref, the drop is excessive. Link may hold a ref, but that doesn’t justify this drop. |

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  

`hci_bind_cis` likely does **not** return a pointer with a reference held (the refcount leak/excess put checker flagged the `hci_conn_drop(cis)` at line 2478). Without a matching get from the bind function, the drop purely decrements an already‑insufficient count, causing the excess‑put warning. Confirmation requires source of `hci_bind_cis`, but the static analysis pattern strongly points to an unbalanced put.
```
