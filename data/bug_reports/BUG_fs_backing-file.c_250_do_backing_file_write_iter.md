# REAL BUG: fs/backing-file.c:250 do_backing_file_write_iter()

**Confidence**: HIGH | **Counter**: `aio->ref.refs.counter`

## Reasoning

| L247 (ret != -EIOCBQUEUED, callback **called** synchronously) | sync return (the buggy path) | YES (2) | YES (2 explicit puts + 1 callback put = 3 total) | ❌ **EXCESS PUT** | Callback drops its ref before cleanup runs → refcount goes negative |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L226 | return ret (sync path before aio alloc) | NO | N/A | ✅ | No aio, no refs |
| L231 | return ret (backing_aio_init_wq failure) | NO | N/A | ✅ | No aio |
| L235 | return -ENOMEM (alloc failure) | NO | N/A | ✅ | No ref held |
| L247 (ret == -EIOCBQUEUED) | async return | YES (refcount_set to 2) | YES (backing_aio_put once, callback will put the second ref later) | ✅ | Async normal path |
| L247 (ret != -EIOCBQUEUED, callback **not** called) | sync return (hypothetical safe case) | YES (2) | YES (backing_aio_put + backing_aio_cleanup → 2 puts) | ✅ | Balanced if callback is never invoked synchronously |
| L247 (ret != -EIOCBQUEUED, callback **called** synchronously) | sync return (the buggy path) | YES (2) | YES (2 explicit puts + 1 callback put = 3 total) | ❌ **EXCESS PUT** | Callback drops its ref before cleanup runs → refcount goes negative |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`vfs_iocb_iter_write` may invoke `backing_aio_queue_completion` synchronously (dropping the IO's reference) while returning a value != `-EIOCBQUEUED`, causing the caller's `backing_aio_cleanup` to perform an additional put that already-released reference, leading to the observed excess put.
```
