# REAL BUG: drivers/gpu/drm/i915/gt/uc/intel_guc_submission.c:286 intel_guc_steal_guc_ids()

**Confidence**: HIGH | **Counter**: `rq->fence.refcount.refcount.refs.counter`

## Reasoning

| Fallthrough after verification (success/EINVAL) | goto err_spin_rq → return 0 or -EINVAL | NO (last already put) | N/A | ✅ | |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L150 (kzalloc_objs fail) | return -ENOMEM | NO (before any get) | N/A | ✅ | |
| L163 (first context create fail) | goto err_wakeref (via err_contexts?) Actually code: after ce[context_index] fail, set ret, goto err_wakeref directly. | NO | N/A | ✅ | |
| L168 (igt_spinner_init fail) | goto err_contexts → err_wakeref | NO (no request refs) | N/A | ✅ | |
| L175 (igt_spinner_create_request fail) | goto err_contexts | NO (spin_rq is error ptr, no valid request ref) | N/A | ✅ | |
| L180 (request_add_spin fail) | goto err_spin_rq | NO (last is NULL, spin_rq has ref but will be put at label) | YES (spin_rq will be put) | ✅ | err_spin_rq handles spin_rq |
| L186 (loop: context create fail) | goto err_spin_rq | YES (last from previous loop iteration holds ref) | NO (err_spin_rq does not put last) | ❌ LEAK | last reference leaked |
| Loop: nop_user_request error, non-EAGAIN or !last, with last non-NULL | goto err_spin_rq | YES (last holds ref) | NO | ❌ LEAK | |
| Loop: nop_user_request error, non-EAGAIN or !last, with last == NULL | goto err_spin_rq | NO (last is NULL) | N/A | ✅ | |
| Normal loop exit (EAGAIN, last non-NULL) | fall through after spin_rq put/wait | YES (last holds ref) | YES (later i915_request_put(last)) | ✅ | |
| After loop: spin_rq wait fail | goto err_spin_rq | NO (last already put before goto) | N/A | ✅ | |
| After loop: steal nop_user_request fail | goto err_spin_rq | NO (last already put) | N/A | ✅ | |
| After loop: steal request wait fail | goto err_spin_rq | NO (rq already put) | N/A | ✅ | |
| After loop: GT idle wait fail | goto err_spin_rq | NO | N/A | ✅ | |
| Fallthrough after verification (success/EINVAL) | goto err_spin_rq → return 0 or -EINVAL | NO (last already put) | N/A | ✅ | |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
The while loop error paths jump to `err_spin_rq` without releasing the `last` request reference obtained from a successful `nop_user_request()`, leaking the refcount.
```
