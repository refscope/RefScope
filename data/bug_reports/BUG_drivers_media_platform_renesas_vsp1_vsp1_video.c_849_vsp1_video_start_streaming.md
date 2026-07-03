# REAL BUG: drivers/media/platform/renesas/vsp1/vsp1_video.c:849 vsp1_video_start_streaming()

**Confidence**: HIGH | **Counter**: `$->stream_config->refcnt.refs.counter`

## Reasoning

| L849 | return 0     | YES (setup succeeded) | NO (held for lifetime) | ✅ (deferred) | ref released later in vsp1_video_stop_streaming |

## Full Response

```
## Path Enumeration

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L825 | error (ret < 0) | NO (setup failed) | YES (cleanup called at L823) | ❌ EXCESS PUT | cleanup unconditionally called when setup likely did not increment refcount |
| L842 | return 0     | NO (condition false) | N/A       | ✅         | setup never called |
| L849 | return 0     | YES (setup succeeded) | NO (held for lifetime) | ✅ (deferred) | ref released later in vsp1_video_stop_streaming |
```

## PRE-VERDICT CHECKLIST

1. **"Held for device lifetime"?** → n/a for this issue; error path is the concern.
2. **"Ownership transferred"?** → not applicable; no ownership transfer on error.
3. **Unconditional GET?** → contract says conditional; on error return, get did not occur → PUT here is an excess decrement.
4. **goto out between GET and PUT?** → no goto; the error path directly calls cleanup after setup failure.

The error path at line 821‑825 always calls `vsp1_video_cleanup_pipeline()` after `vsp1_video_setup_pipeline()` returns a negative value.  The contract for `vsp1_video_setup_pipeline` states the GET (`vsp1_dlm_dl_body_get`) is conditional – it is only performed on successful setup.  Therefore calling the PUT unconditionally on the error path results in a refcount decrement without a matching increment (excess put), exactly matching the warning.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
Error path after `vsp1_video_setup_pipeline()` failure calls `vsp1_video_cleanup_pipeline()` which performs a put without a corresponding get.
```
