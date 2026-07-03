# REAL BUG: fs/btrfs/tests/extent-map-tests.c:332 __test_case_3()

**Confidence**: HIGH | **Counter**: `$->refs.refs.counter`

## Reasoning

| L319-L341 (checks pass, free, out) | return ret (0) | YES | YES | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L270 (goto out after first alloc fail) | error (-ENOMEM) | NO (alloc returned NULL) | N/A | ✅ | |
| L278 (goto out from first add fail) | error (ret < 0) | YES (alloc succeeded at L268) | NO | ❌ LEAK | add failed, em not in tree, caller still holds ref |
| L283-L341 (success flow after free + out) | return ret (0 or error) | YES (alloc then free after add) | YES (free at L283) | ✅ | em freed before out, tree cleanup handles any ref in tree |
| L291 (goto out from second alloc fail) | error (-ENOMEM) | NO (alloc returned NULL) | N/A | ✅ | |
| L304 (goto out from second add fail) | error (ret != 0) | YES (second alloc succeeded) | NO | ❌ LEAK | add failed, em not in tree, ref not released |
| L308 (goto out from !em after add success) | error (-ENOENT) | YES (alloc succeeded, but if em is NULL ref was consumed by tree) | NO (not needed) | ✅ | ownership transferred to tree on add success, tree cleanup handles |
| L317-L341 (checks set ret= -EINVAL then free, then out) | return ret (error) | YES | YES (free at L317) | ✅ | |
| L319-L341 (checks pass, free, out) | return ret (0) | YES | YES | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`btrfs_alloc_extent_map` sets refcount to 1; the first `goto out` after failed `btrfs_add_extent_mapping` (L278) and the second `goto out` after failed `btrfs_add_extent_mapping` (L304) drop the initial reference on `em` without calling `btrfs_free_extent_map`, leaking the extent_map.
```
