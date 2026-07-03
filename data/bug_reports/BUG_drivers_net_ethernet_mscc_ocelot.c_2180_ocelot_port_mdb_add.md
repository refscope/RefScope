# REAL BUG: drivers/net/ethernet/mscc/ocelot.c:2180 ocelot_port_mdb_add()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

| L2180 | success (return ocelot_mact_learn) | YES (get succeeded) | YES (old pgid freed in else branch) | ✅ | new pgid stored, old reference released correctly |

## Full Response

```
| Line | Return Type | GET Done? (ocelot_mdb_get_pgid) | PUT Done? (ocelot_pgid_free) | Balanced? | Notes |
|------|-------------|--------------------------------|------------------------------|-----------|-------|
| L2144 | error (-ENOMEM) | NO (before get) | N/A | ✅ | allocation failure, no refcnt ops |
| L2168 | error (IS_ERR(pgid)) | NO (get failed) | YES (if mc was existing) | ❌ IMBALANCE | else‑branch frees mc->pgid at L2155, get fails → mc->pgid left dangling, future double‑free and excess put |
| L2180 | success (return ocelot_mact_learn) | YES (get succeeded) | YES (old pgid freed in else branch) | ✅ | new pgid stored, old reference released correctly |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the error path at L2168, when mc already exists, ocelot_pgid_free (L2155) releases the old pgid reference, but ocelot_mdb_get_pgid fails and no new reference is stored. mc->pgid remains a dangling pointer, causing an excess put the next time the multicast entry is processed.
```
