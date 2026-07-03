# REAL BUG: fs/fuse/dir.c:927 fuse_create_open()

**Confidence**: HIGH | **Counter**: `$->count.refs.counter`

## Reasoning

| L927 (out_err return) | error | YES (if from out_free_ff) | NO | ❌ LEAK | paths via out_free_ff leak |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L827 (if !forget) | error | NO (ff not allocated) | N/A | ✅ | before ff allocation |
| L830 (if !ff) | error | NO (allocation failed) | N/A | ✅ | ff=NULL |
| L847 (get_create_ext err) | goto out_free_ff | YES (fuse_file_alloc succeeded) | NO (fuse_file_free is not a put) | ❌ LEAK | out_free_ff lacks put |
| L851 (fuse_simple_idmap_request err) | goto out_free_ff | YES | NO | ❌ LEAK | same |
| L856 (invalid inode check) | goto out_free_ff | YES | NO | ❌ LEAK | same |
| L864 (inode=NULL) | error | YES | YES (fuse_sync_release) | ✅ | explicit release |
| L877 (generic_file_open err) | error | YES | YES (fuse_sync_release) | ✅ | |
| L882 (finish_open err) | error | YES | YES (fuse_sync_release) | ✅ | |
| L892 (success) | success | YES | NO (ownership transferred to file) | ✅ | transferred |
| L927 (out_err return) | error | YES (if from out_free_ff) | NO | ❌ LEAK | paths via out_free_ff leak |

[NEED_SOURCE] fuse_file_free

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Three error paths after fuse_file_alloc jump to out_free_ff, which calls fuse_file_free (raw free, no refcount put) instead of the required fuse_sync_release, leaking the initial reference.
```
