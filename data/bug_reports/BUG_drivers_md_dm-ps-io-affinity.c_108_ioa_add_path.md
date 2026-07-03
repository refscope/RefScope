# REAL BUG: drivers/md/dm-ps-io-affinity.c:108 ioa_add_path()

**Confidence**: HIGH | **Counter**: `pi->refcount.refs.counter`

## Reasoning

| L101 return 0 | success | YES (set + possible incs) | YES (dec_and_test at L95 released one ref, others held by path_map entries) | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L52  | error (argc) | NO (before any ref op) | N/A | ✅ | |
| L58  | error (ENOMEM) | NO (pi alloc failed) | N/A | ✅ | |
| L68 goto free_pi | error (zalloc_cpumask_var fail) | YES (refcount_set L63) | NO | ❌ LEAK | initial refcount 1, kfree without put |
| L75 goto free_mask | error (cpumask_parse fail) | YES (refcount_set L63) | NO | ❌ LEAK | initial refcount 1, free_cpumask_var then kfree without put |
| L98 goto free_mask (no mappings) | error (EINVAL) | YES (set) | YES (refcount_dec_and_test at L95 → 0) | ✅ | dec-and-test released ref, then kfree |
| L101 return 0 | success | YES (set + possible incs) | YES (dec_and_test at L95 released one ref, others held by path_map entries) | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`refcount_set` creates an initial reference; error paths at `free_pi` (zalloc_cpumask_var failure) and `free_mask` (cpumask_parse failure) free the object with `kfree()` but never release that reference via `refcount_dec_and_test()`, causing inconsistent refcounting.
```
