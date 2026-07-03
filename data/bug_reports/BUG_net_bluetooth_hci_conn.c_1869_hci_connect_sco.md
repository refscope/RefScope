# REAL BUG: net/bluetooth/hci_conn.c:1869 hci_connect_sco()

**Confidence**: HIGH | **Counter**: `$->refcnt.counter`

## Reasoning

at smatch reports.
- If `sco` was newly allocated by `hci_conn_add_unset()`, a valid initial reference exists and the drop is correct—but the code does not distinguish between the two cases.

### PRE‑

## Full Response

```
## Analysis of `hci_connect_sco()` Refcounting

The warning indicates an **excess put** on `$->refcnt.counter` at line 1869, inside the error-handling branch of `hci_conn_link()`. The path table reveals a critical imbalance when `sco` already exists (returned by lookup instead of newly allocated).

### Path Table

| Line    | Return Type               | SCO GET Done?                                                                 | SCO PUT Done? | Balanced? | Notes |
|---------|---------------------------|-------------------------------------------------------------------------------|---------------|-----------|-------|
| ~1828   | `return acl` (IS_ERR)     | NO (no sco allocated/looked up)                                               | N/A           | ✅ | Error before any sco reference acquired. |
| ~1838   | `hci_conn_drop(acl); return sco` (IS_ERR on create) | NO (sco creation failed)                                                      | N/A           | ✅ | No sco reference exists, acl correctly dropped. |
| **~1867** | `hci_conn_drop(acl); hci_conn_drop(sco); return ERR_PTR(-ENOLINK)` | **NO** when sco was from hash lookup (no get), **YES** when sco was freshly allocated (initial ref) | **YES** | **❌ EXCESS PUT** when sco existed from lookup | **The sco is looked up without taking any new reference; dropping it here causes an extra put → underflow.** |
| ~1857   | `return sco` (success)     | YES (hci_conn_link succeeded → get called)                                    | NO            | ⚠️ (see note)  | Ref held by link; return sco to caller who manages lifecycle. Not part of this warning. |

- The `hci_conn_drop(sco)` at line 1869 (the `!link` path) is **unconditional**, but `sco` may be a pre‑existing connection obtained via `hci_conn_hash_lookup_ba()`. In that case, **no additional reference was acquired** before the `hci_conn_link()` call, so the drop is excessive and triggers the refcount underflow that smatch reports.
- If `sco` was newly allocated by `hci_conn_add_unset()`, a valid initial reference exists and the drop is correct—but the code does not distinguish between the two cases.

### PRE‑VERDICT CHECKLIST

1. **“Held for device lifetime”?** – Not applicable; the sco reference is not held for device lifetime here.  
2. **“Ownership transferred”?** – No documented cleanup stores the sco pointer for later release; both error paths explicitly attempt to release it.  
3. **Unconditional GET?** – Not relevant; the GET is conditional on sco origin. The unconditional drop is the problem.  
4. **goto out between GET and PUT?** – Not applicable; direct return path with explicit put.

### Verdict

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`hci_conn_drop(sco)` is called unconditionally on the `!link` error path, even when `sco` was obtained via `hci_conn_hash_lookup_ba()` without taking a reference, causing an excess put on the sco connection’s refcount.
```
