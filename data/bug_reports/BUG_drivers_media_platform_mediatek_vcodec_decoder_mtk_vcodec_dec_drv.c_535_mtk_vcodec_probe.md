# REAL BUG: drivers/media/platform/mediatek/vcodec/decoder/mtk_vcodec_dec_drv.c:535 mtk_vcodec_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L524 (return 0) | success | YES (if is_subdev_supported) | N/A (intentional) | ✅ | devices remain active, no leak |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L358 | return -ENOMEM | NO (before get) | N/A | ✅ | devm_kzalloc failed |
| L367 | return -EINVAL | NO | N/A | ✅ | chip_name invalid |
| L383 | return -ENODEV | NO | N/A | ✅ | no VPU/SCP handle |
| L388 | return PTR_ERR | NO | N/A | ✅ | fw_handler IS_ERR |
| L395 (goto err_dec_pm) | error | NO | N/A | ✅ | init resources failed |
| L405 (goto err_res) | error | NO | N/A | ✅ | core_workqueue alloc failed |
| L433 (goto err_core_workq) | error | NO | N/A | ✅ | v4l2_device_register failed |
| L441 (goto err_dec_alloc) | error | NO | N/A | ✅ | video_device_alloc failed |
| L455 (goto err_dec_alloc) | error | NO | N/A | ✅ | m2m_dev init failed |
| L466 (goto err_event_workq) | error | NO | N/A | ✅ | decode_workqueue alloc failed |
| L476 (goto err_reg_cont) | error (populate fail) | YES (partial) | NO | ❌ LEAK | of_platform_populate partially created devices; no depopulate |
| L490 (goto err_reg_cont) | error (video reg fail) | YES (if is_subdev_supported) | NO | ❌ LEAK | no of_platform_depopulate |
| L511 (goto err_dec_mem_init) | error (media ctrl fail) | YES (if is_subdev_supported) | NO | ❌ LEAK | no depopulate |
| L518 (goto err_media_reg) | error (media dev fail) | YES (if is_subdev_supported) | NO | ❌ LEAK | no depopulate |
| L524 (return 0) | success | YES (if is_subdev_supported) | N/A (intentional) | ✅ | devices remain active, no leak |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

`of_platform_populate` success (or partial failure) creates devices with krefs that are never released on error paths; the code jumps to `err_reg_cont` / `err_dec_mem_init` / `err_media_reg` without calling `of_platform_depopulate`. This leaks the kref of any registered platform devices.
```
