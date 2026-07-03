# REAL BUG: drivers/infiniband/hw/hns/hns_roce_cq.c:479 hns_roce_create_cq()

**Confidence**: HIGH | **Counter**: `$->refcount.refs.counter`

## Reasoning

- goto out between GET and PUT? The jumps to `err_cq_db` and `err_cqn` land in a cascade that deliberately excludes `free_cqc`.

## Full Response

```
```
| Line | Return Type        | GET Done?                          | PUT Done?                    | Balanced? | Notes                                                                                    |
|------|--------------------|------------------------------------|------------------------------|-----------|------------------------------------------------------------------------------------------|
| 409  | goto err_out       | NO (before any get)                | N/A                          | ✅        | Early check before any ref acquisition.                                                  |
| 414  | goto err_out       | NO                                 | N/A                          | ✅        | verify_cq_create_attr failure.                                                           |
| 419  | goto err_out       | NO                                 | N/A                          | ✅        | udata copy failure.                                                                      |
| 426  | goto err_out       | NO                                 | N/A                          | ✅        | set_cqe_size failure.                                                                    |
| 431  | goto err_out       | NO                                 | N/A                          | ✅        | alloc_cq_buf failure.                                                                    |
| 437  | goto err_cq_buf    | NO (alloc_cq_db failed → no ref)   | N/A                          | ✅        | Conditional get, error path means no reference held.                                     |
| 443  | goto err_cq_db     | YES (alloc_cq_db succeeded)        | NO (err_cq_db skips free_cqc)| ❌ LEAK   | Missing free_cqc after successful alloc_cq_db when alloc_cqn fails.                      |
| 450  | goto err_cqn       | YES                                | NO (err_cqn skips free_cqc)  | ❌ LEAK   | alloc_cqc failure jumps to err_cqn which does not call free_cqc.                          |
| 458  | goto err_cqc       | YES                                | YES (err_cqc calls free_cqc) | ✅        | ib_copy_to_udata error correctly releases the ref via free_cqc cascade.                  |
| 466  | return 0           | YES                                | Not required (lifetime ref)  | ✅        | Success return stores the initial ref, no immediate put needed.                          |
| 479  | return ret (from err_out via leaked paths) | YES (on paths 443/450) | NO | ❌ LEAK | Both error paths (alloc_cqn, alloc_cqc failures) end here with an unresolved ref.        |

**Pre‑verdict checklist answers**:
- “Held for device lifetime”? Not applicable to error paths; those paths must explicitly release.
- “Ownership transferred”? No. No cleanup code elsewhere will release this reference on these error returns.
- Unconditional GET? alloc_cq_db is conditional, but after success, every error return must call free_cqc.
- goto out between GET and PUT? The jumps to `err_cq_db` an
```
