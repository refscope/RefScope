# REAL BUG: drivers/usb/core/hcd.c:2249 ehset_single_step_set_feature()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

he kref, but the only `usb_put_urb` matching it is at L2236 — which is unreachable from these paths. Only `usb_free_urb` at L2249 runs, releasing the initial allocation reference but **not** the `usb_get_urb` reference. The refcount ends at 1 → URB never freed (memory leak + refcount leak).

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L2189 | error return | NO (before URB alloc) | N/A | ✅ | No URB exists |
| L2192 | error return | NO (before URB alloc) | N/A | ✅ | No URB exists |
| L2197 | error return | NO (before URB alloc) | N/A | ✅ | No URB exists |
| L2212 | goto cleanup | NO (urb=NULL) | N/A | ✅ | `request_single_step_set_feature_urb` returned NULL |
| L2216 | goto out1 | YES (init ref only) | YES (`usb_free_urb` at L2249) | ✅ | No `usb_get_urb` yet; one alloc ref released |
| L2223 | goto out1 | YES (init ref only) | YES (`usb_free_urb` at L2249) | ✅ | No `usb_get_urb` yet; `usb_kill_urb` doesn't release caller refs |
| L2237 | goto out1 | YES (init + `usb_get_urb` at L2232) | YES (`usb_put_urb` L2236 + `usb_free_urb` L2249) | ✅ | Extra ref from `usb_get_urb` released at L2236 |
| L2240→L2247→L2248 | fallthrough to out1 | YES (init + `usb_get_urb` at L2232) | PARTIAL (only `usb_free_urb` L2249) | ❌ LEAK | `usb_get_urb` ref NOT released; only init ref freed |

**Explanation of L2240→L2248 leak paths:**

After `map_urb_for_dma` succeeds (L2235 condition false), the code at L2240-L2247 runs and always falls through to `out1` (L2248) → `usb_free_urb(urb)` (L2249). This includes:
- `submit_single_step_set_feature` returns non-zero (submission failed)
- Submission succeeds but wait times out (`usb_kill_urb` is called but doesn't release caller's ref)
- Submission succeeds and completes normally

On ALL these paths, `usb_get_urb(urb)` at L2232 incremented the kref, but the only `usb_put_urb` matching it is at L2236 — which is unreachable from these paths. Only `usb_free_urb` at L2249 runs, releasing the initial allocation reference but **not** the `usb_get_urb` reference. The refcount ends at 1 → URB never freed (memory leak + refcount leak).

## PRE-VERDICT CHECKLIST

1. **"Held for device lifetime"?** — No. This is a one-shot URB for a USB control transfer, allocated and freed within the same function. No deferred lifetime.
2. **"Ownership transferred"?** — No. The function explicitly calls `usb_free_urb(urb)` at the end, retaining ownership. HCD takes its own internal ref on submit, separate from the caller's `usb_get_urb`.
3. **"Unconditional GET"?** — The `usb_get_urb` contract says "conditional_on_nonnull", but `urb` is guaranteed non-NULL at L2232 (checked at L2211). So GET=YES on ALL paths after L2232. Every return after L2232 must release TWO refs; only one is released.
4. **"goto out between GET and PUT"?** — The only goto (`L2237`) correctly has `usb_put_urb` first. But the **fallthrough** paths (L2240→L2247→L2248) have no `usb_put_urb` — the GET reference leaks.

---

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`usb_get_urb(urb)` at L2232 acquires an extra kref that is only released on the `map_urb_for_dma` failure path (L2236). All normal completion paths (L2240→L2247) fall through to `out1` where only `usb_free_urb` release
```
