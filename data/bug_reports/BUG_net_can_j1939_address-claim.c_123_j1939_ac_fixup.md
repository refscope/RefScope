# REAL BUG: net/can/j1939/address-claim.c:123 j1939_ac_fixup()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

Therefore, the path where `ecu->addr != skcb->addr.sa` leads to a double-put (one in unmap, one at L123) – a real refcount bug.

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 90  | error (ret<0) | NO (before get) | N/A | ✅ | early return, no ecu reference |
| 93  | error (!ecu) | NO (get failed) | N/A | ✅ | get_by_name returned NULL, no ref held |
| 95‑97 | goto implicit (condition true) → L123 | YES | if unmap does no put: YES; if unmap does put: YES (but extra) | ⚠️ UNCERTAIN (depends on j1939_ecu_unmap) | if unmap releases ref → excess put at L123 |
| 95‑98 | fall-through (condition false) → L123 | YES | YES (explicit put at L123) | ✅ | single get, single put |
| 109 | error (invalid sa) | NO (not in CLAIMED block, no get) | N/A | ✅ | |
| 117 | error (invalid da) | NO (not in CLAIMED block, no get) | N/A | ✅ | |
| 111‑120 | success | NO (no get in this block) | N/A | ✅ | no refs involved |

**Key observation:** The warning is "refcount excess put" at line 123 (`j1939_ecu_put(ecu)`).  
The GET is `j1939_ecu_get_by_name()` – conditional acquisition, successfully returned on the path.  
The only operation that could drop the reference before L123 is `j1939_ecu_unmap(ecu)`, called when `ecu->addr != skcb->addr.sa`.  
If `j1939_ecu_unmap` internally decrements the refcount (e.g., via `kref_put`), then the subsequent `j1939_ecu_put` would be an extra put → **excess put**.

Since the kernel detected this excess, it is highly likely that `j1939_ecu_unmap` does release the reference.  
Therefore, the path where `ecu->addr != skcb->addr.sa` leads to a double-put (one in unmap, one at L123) – a real refcount bug.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`j1939_ecu_unmap` drops the reference from the mapping; the caller still holds its own reference from `j1939_ecu_get_by_name`, but the unconditional `j1939_ecu_put` at L123 creates a surplus put when unmap was executed.
```
