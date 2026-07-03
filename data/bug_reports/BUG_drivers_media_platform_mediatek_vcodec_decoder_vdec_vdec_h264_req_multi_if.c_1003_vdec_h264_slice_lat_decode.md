# REAL BUG: drivers/media/platform/mediatek/vcodec/decoder/vdec/vdec_h264_req_multi_if.c:1003 vdec_h264_slice_lat_decode()

**Confidence**: HIGH | **Counter**: `$->ctx->msg_queue.core_list_cnt.counter`

## Reasoning

| L961 (return 0, racing, core qbuf already done at L928) | success | YES | ownership transfer | ✅ | |

## Full Response

```
| Path | Return Type | GET (core_ctx qbuf)? | PUT (core_ctx dqbuf / lat_ctx qbuf)? | Balanced? | Notes |
|------|-------------|------------------------|----------------------------------------|-----------|-------|
| L899 (vdec_msg_queue_init fail) → return -ENOMEM | error | NO | N/A | ✅ | |
| L905 (bs NULL) → return vpu_dec_reset(vpu) | special | NO | N/A | ✅ | |
| L908 (is_field_bitstream) → return -EINVAL | error | NO | N/A | ✅ | |
| L911 (dqbuf lat_ctx fails) → return -EAGAIN | error | NO | N/A | ✅ | |
| L915 (nal_start_idx < 0) → goto err_free_fb_out | error | NO | lat_ctx qbuf at label | ✅ | puts buffer back to lat queue |
| L917 (fill_decode error) → goto err_free_fb_out | error | NO | lat_ctx qbuf | ✅ | |
| L921 (resolution_changed alloc_mv_buf error) → goto err_free_fb_out | error | NO | lat_ctx qbuf | ✅ | |
| L925 (vpu_dec_start fails) → goto err_free_fb_out | error | NO | lat_ctx qbuf | ✅ | |
| **L938→L946 (IS_VDEC_INNER_RACING true, vpu_dec_end returns SLICE_HEADER_FULL / TRANS_BUFFER_FULL) → return -EINVAL** | **error** | **YES** (core_ctx qbuf at L928 inside `if`) | **NO** (no core dqbuf; lat qbuf only for !racing) | **❌ LEAK** | core_list_cnt counter never released |
| L928→L946 (IS_VDEC_INNER_RACING false, vpu_dec_end returns those errors) → return -EINVAL | error | NO | lat_ctx qbuf before return | ✅ | |
| L961 (return 0, non‑racing, after core qbuf at L950) | success | YES | ownership transfer | ✅ | queue will release later |
| L961 (return 0, racing, core qbuf already done at L928) | success | YES | ownership transfer | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
On the error path (vpu_dec_end returns SLICE_HEADER_FULL/TRANS_BUFFER_FULL) when IS_VDEC_INNER_RACING is true, `vdec_msg_queue_qbuf(&core_ctx, lat_buf)` was already executed, incrementing the core_list_cnt counter, but the function returns -EINVAL without any corresponding dequeue or re‑queue to the lat_ctx, leaving the buffer stuck in the core queue and leaking the counter.
```
