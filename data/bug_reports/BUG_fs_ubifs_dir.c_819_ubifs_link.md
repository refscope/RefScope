# REAL BUG: fs/ubifs/dir.c:819 ubifs_link()

**Confidence**: HIGH | **Counter**: `$->i_count.counter`

## Reasoning

| L795+ (success) | return 0  | YES (ihold at L786) | NO  | ❌ **LEAK** | success path: `d_instantiate`, `fscrypt_free_filename`, `return 0` — no `iput` for the `ihold` |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L768 | error       | NO (before ihold) | N/A  | ✅ | `fscrypt_prepare_link` error |
| L772 | error       | NO (before ihold) | N/A  | ✅ | `fscrypt_setup_filename` error |
| L776 | goto out_fname | NO (before ihold) | N/A  | ✅ | `dbg_check_synced_i_size` or `ubifs_budget_space` error; `out_fname` only calls `fscrypt_free_filename`, no `iput` |
| L780 | goto out_fname | NO (before ihold) | N/A  | ✅ | same as above |
| L791 | goto out_cancel | YES (ihold at L786) | YES (`iput` in `out_cancel`) | ✅ | error from `ubifs_jnl_update`, then `iput(inode)` |
| L795+ (success) | return 0  | YES (ihold at L786) | NO  | ❌ **LEAK** | success path: `d_instantiate`, `fscrypt_free_filename`, `return 0` — no `iput` for the `ihold` |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`ihold(inode)` unconditionally increments the inode refcount at L786, but the success path returns without calling `iput(inode)`. The `d_instantiate()` acquires its own reference, so the extra `ihold` reference is leaked on successful link. This is a classic refcount leak.
```
