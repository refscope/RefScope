# REAL BUG: fs/nfs/blocklayout/blocklayout.c:439 bl_write_pagelist()

**Confidence**: HIGH | **Counter**: `$->refcnt.refcount.refs.counter`

## Reasoning

`pnfs_callback` (or the bio end‑io chain) when all I/O finishes. The synchronous `put_parallel` therefore constitutes an extra release. Smatch’s “refcount excess put” on line 439 correctly flags that the reference count can become zero before this call, leading to a double‑free or use‑after‑free.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L390 (approx) | `return PNFS_NOT_ATTEMPTED` | NO (par is NULL) | N/A | ✅ | alloc_parallel failed |
| `goto out` after `ext_tree_lookup` failure | goto | YES | YES (at L439) | ❌ EXCESS | `par` passed to bio(s) holds reference; put_parallel here will lead to double release when bio completes |
| `goto out` after `do_add_page_to_bio` error | goto | YES | YES (at L439) | ❌ EXCESS | same reason — outstanding bios may hold references |
| Fallthrough after loop ends | fallthrough to `out:` | YES | YES (at L439) | ❌ EXCESS | all bios submitted; put_parallel here conflicts with I/O completion callback releasing the reference |

All paths after `alloc_parallel` reach `put_parallel(par)` at line 439. The pattern in NFS blocklayout is that `bl_write_pagelist` submits bios and transfers ownership of the `parallel_io` to the I/O completion layer; the final reference is released by the `pnfs_callback` (or the bio end‑io chain) when all I/O finishes. The synchronous `put_parallel` therefore constitutes an extra release. Smatch’s “refcount excess put” on line 439 correctly flags that the reference count can become zero before this call, leading to a double‑free or use‑after‑free.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`bl_write_pagelist` incorrectly calls `put_parallel` after transferring `par` to the I/O subsystem; the completion callback already releases the reference, so the synchronous put causes a refcount underflow and potential double free.
```
