# REAL BUG: fs/nfs/pnfs.c:3129 pnfs_generic_pg_writepages()

**Confidence**: HIGH | **Counter**: `hdr->lseg->pls_refcount.refs.counter`

## Reasoning

| 3127 | success (ret == 0) | YES                       | YES (pnfs_do_write likely consumes the ref) | ✅?        | pnfs_do_write is called; it presumably eventually calls pnfs_put_lseg or transfers ownership. Static analysis flagged the leak. |

## Full Response

```
| Line | Return Type        | GET Done?                 | PUT Done?            | Balanced? | Notes                                                                                                                          |
|------|--------------------|---------------------------|----------------------|-----------|--------------------------------------------------------------------------------------------------------------------------------|
| 3118 | error (-ENOMEM)    | NO  (before get)          | N/A                  | ✅         | hdr allocation failed, no lseg.                                                                                                |
| 3127 | error (ret != 0)   | YES (desc->pg_lseg non‑NULL) | NO (pnfs_do_write not called) | ❌ LEAK    | pnfs_get_lseg at 3122 took a ref; when nfs_generic_pgio fails (ret!=0) we return without any matching put.                     |
| 3127 | success (ret == 0) | YES                       | YES (pnfs_do_write likely consumes the ref) | ✅?        | pnfs_do_write is called; it presumably eventually calls pnfs_put_lseg or transfers ownership. Static analysis flagged the leak. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pnfs_get_lseg` unconditionally increments the lseg refcount when `desc->pg_lseg` is non‑NULL. On the error return where `nfs_generic_pgio` returns non‑zero, the function skips `pnfs_do_write` (which is the only path that would release the reference), leaking the ref on every such error.
```
