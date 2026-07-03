# REAL BUG: drivers/gpu/drm/xe/xe_oa.c:1888 xe_oa_stream_open_ioctl_locked()

**Confidence**: HIGH | **Counter**: `$->xef->refcount.refcount.refs.counter`

## Reasoning

- All other error paths after a successful init go through `err_destroy` and correctly balance the reference. The success path passes the reference to the stream, which is eventually released when the fd is closed.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1832 (goto exit after exclusive check) | error (-EBUSY) | NO (no stream, no xef get) | N/A | ✅ | No allocation at all. |
| L1837 (drm_syncobj_create fail → goto exit) | error (ret) | NO | N/A | ✅ | No stream created. |
| L1843 (kzalloc fail → goto err_syncobj → exit) | error (-ENOMEM) | NO | N/A | ✅ | Only syncobj, no stream. |
| L1851 (xe_oa_parse_syncs fail → goto err_free → exit) | error (ret) | Possibly YES (parse_syncs may get xef via sync entries) | Conditional: sync cleanup loop may put xef refs | ⚠️ uncertain | Sync cleanup likely handles it; not primary suspect. |
| L1860 (xe_oa_stream_init fail → goto err_free → exit) | error (ret) | **YES** (xe_oa_stream_init acquires xef reference) | **NO** (err_free only kfree(stream), no xe_oa_stream_destroy) | ❌ LEAK | xef ref taken inside init, never released on this error path. |
| L1870 (xe_oa_enable_locked fail → goto err_destroy → exit) | error (ret) | YES (xef ref from init) | YES (destroy → xe_file_put) | ✅ | Destroy does full teardown. |
| L1876 (anon_inode_getfd fail → goto err_disable → err_destroy → exit) | error (ret) | YES (xef ref from init) | YES (disable + destroy) | ✅ | Full cleanup. |
| L1878 (success, return stream_fd) | success (≥0) | YES (xef ref held by stream) | N/A (held for stream lifetime) | ✅ | Reference held until fd close triggers destroy. |

**Analysis:**
- `xe_oa_stream_init` is the only place where a reference on `xef` (xe_file) can be taken, because `xe_oa_stream_destroy` does `xe_file_put` (as per its contract) and the stream structure must hold that reference.
- The error path after a failed `xe_oa_stream_init` currently jumps to `err_free`, which only `kfree(stream)` and then falls through to `err_syncobj` → `exit`. There is no call to `xe_oa_stream_destroy` (which would release the xef reference) nor any explicit `xe_file_put`. This means the reference taken by `xe_oa_stream_init` leaks.
- All other error paths after a successful init go through `err_destroy` and correctly balance the reference. The success path passes the reference to the stream, which is eventually released when the fd is closed.

**PRE-VERDICT CHECKLIST:**
1. **"Held for device lifetime"?** No – the stream is not device lifetime; it is per-open. Error paths must release.
2. **"Ownership transferred"?** No – the stream is not added to any persistent list before the error, so ownership is not transferred.
3. **Unconditional GET?** The `xe_oa_stream_init` contract lists unconditional side effects (always calls `xe_oa_get_oa_config`), and it must also take the xef reference unconditionally. Even if init fails after the get, that ref is held.
4. **goto out between GET and PUT?** Yes – after `xe_oa_stream_init` failure, `goto err_free` lands in a label that does NOT call `xe_oa_stream_destroy`, only `kfree`.

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`xe_oa_stream_init` 
```
