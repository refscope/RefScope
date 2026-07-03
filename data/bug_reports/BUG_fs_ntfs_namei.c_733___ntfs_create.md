# REAL BUG: fs/ntfs/namei.c:733 __ntfs_create()

**Confidence**: HIGH | **Counter**: `$->count.counter`

## Reasoning

ror (all goto err_out after alloc) | YES (from ntfs_mft_record_alloc) | YES (ntfs_mft_record_free at 721 – contains put) + YES (unmap_mft_record at 724) | ❌ **excess put** | ntfs_mft_record_free already releases the reference; explicit unmap afterwards is an extra put → refcount drops below zero |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| 415 | error (‑ENOMEM) | NO (before alloc) | N/A | ✅ | No MFT ref obtained |
| 491 | error (alloc fails) | NO (alloc sets err) | N/A | ✅ | ntfs_mft_record_alloc fails, ni not referenced |
| 696 | success (return ni) | YES (from ntfs_mft_record_alloc) | YES (unmap_mft_record at 682) | ✅ | One put, balanced |
| 733 | error (all goto err_out after alloc) | YES (from ntfs_mft_record_alloc) | YES (ntfs_mft_record_free at 721 – contains put) + YES (unmap_mft_record at 724) | ❌ **excess put** | ntfs_mft_record_free already releases the reference; explicit unmap afterwards is an extra put → refcount drops below zero |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`ntfs_mft_record_free` already puts the reference acquired by `ntfs_mft_record_alloc` (or internally unmaps), so the subsequent `unmap_mft_record(ni)` on the error path is an extra put, causing the detected refcount excess.
```
