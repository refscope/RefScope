# REAL BUG: drivers/of/base.c:1660 of_parse_phandle_with_args_map()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L1632 | goto put (!match after inner while) | CUR: YES; NEW: YES (last found, may equal cur) | CUR: YES; NEW: YES | ❌ Same as above | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1551 | return -EINVAL | NO (before any get) | N/A | ✅ | index < 0 |
| L1554 | return -ENOMEM | NO | N/A | ✅ | memory allocation failure |
| L1558 | if (ret) return ret | NO (cur not set, out_args->np not valid on error) | N/A | ✅ | early return on parse failure |
| L1564 | goto put (of_property_read_u32 fail) | CUR: YES (L1562) | CUR: YES; NEW: NULL | ✅ | |
| L1574 | return 0 (no map) | CUR: YES | CUR: NO (explicit) | ✅ (transfer) | Success, ownership transferred to `out_args->np`; caller will `of_node_put`. |
| L1587 | goto put (!new) | CUR: YES; NEW: NO (NULL) | CUR: YES; NEW: NULL put | ✅ | |
| L1603 | goto put (read prop of new fails) | CUR: YES; NEW: YES (non-NULL from `of_find_node_by_phandle`) | CUR: YES; NEW: YES | ❌ EXCESS if `cur == new` → double put of same node | Possible double put |
| L1608 | goto put (WARN/malformed) | CUR: YES; NEW: YES | CUR: YES; NEW: YES | ❌ Same as above | |
| L1632 | goto put (!match after inner while) | CUR: YES; NEW: YES (last found, may equal cur) | CUR: YES; NEW: YES | ❌ Same as above | |

**PRE-VERDICT CHECKLIST**

1. **"Held for device lifetime"?** No, this is a parser function; no probe‑remove pattern.
2. **"Ownership transferred"?** Only for the `return 0` path (explicit, caller gets `out_args->np`). All `goto put` paths are error returns with no transfer -> must release `cur` and `new`.
3. **Unconditional GET?** `of_find_node_by_phandle` returns node with incremented refcount if non‑NULL; `new` holds a reference on all error paths inside the inner loop.
4. **goto out between GET and PUT?** Multiple `goto put` paths inside the inner while where `new` is non‑NULL and `cur` is also non‑NULL. The `put:` label unconditionally does `of_node_put(cur); of_node_put(new);`. If `cur == new`, this does a double put on the same node, causing a refcount excess put (and use‑after‑free if it is the last reference).

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`of_find_node_by_phandle` can return the same node as `cur` (self‑referencing phandle). On multiple error paths (L1603, L1608, L1632), both `cur` and `new` are put without any identity check, leading to a double put and an excess refcount drop when they alias.
```
