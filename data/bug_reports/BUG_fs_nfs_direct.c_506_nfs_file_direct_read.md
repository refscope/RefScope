# REAL BUG: fs/nfs/direct.c:506 nfs_file_direct_read()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| L477‑L506 (nfs_direct_read_schedule_iovec called, then fall to out_release) | return result | YES (alloc) | YES (schedule consumes ref) + YES (L506) | ❌ EXCESS PUT | schedule already released dreq, then L506 releases again |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L444 (count==0 → out) | return 0 | NO (before alloc) | N/A | ✅ | No dreq allocated |
| L451 (dreq==NULL → out) | return -ENOMEM | NO (alloc failed) | N/A | ✅ | No dreq, no ref |
| L458‑460 (IS_ERR(l_ctx) block → nfs_direct_req_release(dreq); goto out_release → L506 nfs_direct_req_release) | return error | YES (alloc succeeded) | YES ×2 | ❌ EXCESS PUT | dreq released once here, then again at L506 |
| L470‑474 (nfs_start_io_direct error → nfs_direct_req_release(dreq); goto out_release → L506) | return error | YES | YES ×2 | ❌ EXCESS PUT | same double‑release |
| L477‑L506 (nfs_direct_read_schedule_iovec called, then fall to out_release) | return result | YES (alloc) | YES (schedule consumes ref) + YES (L506) | ❌ EXCESS PUT | schedule already released dreq, then L506 releases again |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
nfs_direct_read_schedule_iovec() unconditionally consumes the dreq reference, but `out_release` at L506 still calls nfs_direct_req_release(dreq), leading to a double‑put (excess put on the kref).
```
