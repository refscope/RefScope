# REAL BUG: drivers/iio/buffer/industrialio-triggered-buffer.c:97 iio_triggered_buffer_setup_ext()

**Confidence**: MEDIUM | **Counter**: `$->ref.refcount.refs.counter`

## Reasoning

Without the source of `iio_device_attach_buffer()` we cannot be 100% certain, but the combination of the unconditional get contract and the “excess put” warning at the `iio_kfifo_free` line makes this a highly likely real bug.

## Full Response

```
## Path Table

| Line | Return Type                     | GET Done? (iio_buffer_get) | PUT Done? (iio_kfifo_free/put) | Balanced? | Notes |
|------|---------------------------------|----------------------------|--------------------------------|-----------|-------|
| L44  | error (return -EADDRINUSE)      | NO (before alloc, no get)  | N/A                            | ✅        | early return, no buffer |
| L53  | goto error_ret                  | NO (alloc failed)          | N/A                            | ✅        | buffer == NULL, no ref |
| L62  | goto error_kfifo_free           | Allocation GET (ref=1)     | YES (iio_kfifo_free at L97)    | ✅        | single put, correct |
| L75  | goto error_dealloc_pollfunc     | Allocation GET + **iio_device_attach_buffer GET (unconditional, ref +1 → total ref=2)** | YES (iio_kfifo_free at L97, **only 1 put**) | ❌ LEAK | attach failed after get, only 1 put → ref remains at 1 → leak (assuming attach does **not** already put on failure) |
| L77  | return 0 (success)              | Allocation GET + attach GET (ref=2) | NO in this function (cleanup deferred) | ✅ (defer) | ownership transfer, cleanup handled by iio_triggered_buffer_cleanup() |

**Critical observation**: The warning is “excess put”, not “leak”.  
If `iio_device_attach_buffer()` performs a **put** on its own failure (which is common in the kernel for unconditional‑get functions), then the refcount after an attach‑failure path would be:
- Alloc ref=1 → attach get (ref=2) → attach internal put on failure (ref=1) → error path’s `iio_kfifo_free` puts again (ref=0) → **double free / excess put** (because the buffer is already freed by the internal put that triggered the kref release).  

That matches the “excess put” warning at line 97 exactly.  

Without the source of `iio_device_attach_buffer()` we cannot be 100% certain, but the combination of the unconditional get contract and the “excess put” warning at the `iio_kfifo_free` line makes this a highly likely real bug.

[NEED_SOURCE] iio_device_attach_buffer

## VERDICT: REAL_BUG
## CONFIDENCE: MEDIUM
The error path after `iio_device_attach_buffer` failure (L75) calls `iio_kfifo_free(buffer)` at L97, which releases one reference. If `iio_device_attach_buffer` already performs a put on its internal failure (standard kernel pattern), this results in a double‑put and an “excess put” kref underflow—matching the warning. The immediate fix is to skip the `iio_kfifo_free` call when `iio_device_attach_buffer` fails, because the buffer’s cleanup would already be handled by the attach routine on its error path.
```
