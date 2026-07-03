# REAL BUG: fs/zonefs/super.c:1056 zonefs_init_zgroup()

**Confidence**: HIGH | **Counter**: `$->s_fs_info->s_active_seq_files.counter`

## Reasoning

| L1039 | success | YES | will PUT later (mount/unmount cleanup) | ✅ | normal mount path; counters to be released on unmount/file eviction |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L949 | early return | NO (before any processing) | N/A | ✅ | g_nr_zones == 0, no zones to account |
| L952 | error | NO (before any zones) | N/A | ✅ | kvzalloc_objs failed, no zones instantiated |
| L962 | error (WARN) | YES (for all previously processed zones, n≥1) | NO | ❌ LEAK | GET executed for all prior zones; return skips any cleanup |
| L1001 | error (size check) | Conditional: n=0 → NO; n>0 → YES for prior zones | NO | ❌ LEAK (if n>0) | Zone size check before current zone's GET; prior GETs not released |
| L1022 | error (zone mgmt fail) | Conditional: n=0 → NO; n>0 → YES for prior zones | NO | ❌ LEAK (if n>0) | Similar to L1001; zonefs_zone_mgmt error before GET of current zone |
| L1033 | error (post-loop) | YES (for all zones processed, n times) | NO | ❌ LEAK | Loop finished with n != expected; every accounted zone leaks |
| L1039 | success | YES | will PUT later (mount/unmount cleanup) | ✅ | normal mount path; counters to be released on unmount/file eviction |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`zonefs_account_active` increments `s_active_seq_files.counter` for each zone. On all error paths after at least one zone has been processed (lines 962, 1001, 1022, 1033), the function returns without any corresponding decrement. The refcount leak is permanent because the mount fails and the superblock is torn down without ever releasing the per-zone counts.
```
