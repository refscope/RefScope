# REAL BUG: net/bridge/br_fdb.c:457 fdb_add_local()

**Confidence**: HIGH | **Counter**: `$->fdb_n_learned.counter`

## Reasoning

4. **goto out between GET and PUT?** No goto; the put happens before a potential later get.

## Full Response

```
## Path Table

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L435–436 | error (-EINVAL) | NO (no get) | NO | ✅ | fdb not touched |
| L438–444 | success (0) | NO (no get) | NO | ✅ | fdb exists and is local; no delete/create |
| L438–446 | goto fallthrough | NO at this point | YES (via fdb_delete) | ⚠️ **EXCESS PUT** on fdb_n_learned | fdb_delete decrements learned counter unconditionally, but the entry may not be learned (e.g., static) |
| L449–452 | error (-ENOMEM) | NO (fdb_create failed) | NO | ✅ | no ref acquired |
| L449–456 | success (0) | YES (fdb_create succeeded) | NO (but ref held by caller/hash) | ✅ normal success path | initial ref for new entry, no learned counter involved |
```

**Note**: The warning targets `fdb_n_learned.counter` excess put; this map pinpoints line 446 as the put site that can underflow.

## Pre-Verdict Checklist

1. **"Held for device lifetime"?** Not applicable. The learned counter is not held for device lifetime; it tracks dynamic entries only.
2. **"Ownership transferred"?** No transfer exists; the decrement in `fdb_delete` is unconditional on entry type.
3. **Unconditional GET?** Not applicable. The excess is a **put** on a counter that was never incremented for static entries.
4. **goto out between GET and PUT?** No goto; the put happens before a potential later get.

## Verdict

VERDICT: REAL_BUG  
CONFIDENCE: HIGH

**Reasoning**: `fdb_delete` is called on an existing FDB entry that is not local, but it may be a static (non-learned) entry. Since `fdb_delete` unconditionally decrements `fdb_n_learned`, a static entry will cause an excess put (underflow) because its learned counter was never incremented. The code lacks a check for `BR_FDB_LEARNED` before deletion.
```
