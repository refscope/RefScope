# REAL BUG: net/bluetooth/l2cap_core.c:438 l2cap_chan_timeout()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

The early return when `conn == NULL` leaks a reference but that is a separate issue – the warning is explicitly about an excess put, which is caused by the double-put on the normal path.

## Full Response

```
## Path Table

| Path | Line(s) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|---------|-------------|-----------|-----------|-----------|-------|
| Early return | `if (!conn) return;` | early void return | **YES** (work holds ref) | **NO** | ❌ LEAK | The work item was scheduled with `l2cap_chan_hold`, so this path leaks a ref – but this is a **leak, not an excess put** |
| Normal execution | all lines after `if (!conn)` – final `l2cap_chan_put(chan)` at L438 | function end | **YES** (work holds ref) | **YES** (explicit `l2cap_chan_put` at L438) + **EXTRA PUT** inside `l2cap_chan_close` | ❌ EXCESS PUT | `l2cap_chan_close` internally calls `l2cap_chan_put`, releasing the work's hold → the explicit put at L438 is a double-put that causes refcount underflow |

**Detailed analysis of the normal path:**

- The work item is scheduled with a reference taken by `__set_chan_timer()` via `l2cap_chan_hold(chan)` (contract says `l2cap_chan_hold` is a standard get → `kref_get`).
- Inside `l2cap_chan_timeout()`, after ensuring `conn` is not NULL, the function calls `l2cap_chan_close(chan, reason)`.
- **Crucially**, `l2cap_chan_close()` (as found in the kernel, e.g., `net/bluetooth/l2cap_core.c`) performs:
  ```c
  l2cap_chan_lock(chan);
  ...
  l2cap_chan_unlock(chan);
  ...
  l2cap_chan_put(chan);   /* releases the reference held by the caller */
  ```
- Therefore, **`l2cap_chan_close` already releases the reference** that was held for the work item.
- When `l2cap_chan_timeout()` subsequently calls `l2cap_chan_put(chan)` at line 438, it releases the same reference a second time → refcount goes to zero (or below) → `refcount excess put` warning is triggered.

The early return when `conn == NULL` leaks a reference but that is a separate issue – the warning is explicitly about an excess put, which is caused by the double-put on the normal path.

## VERDICT: REAL_BUG
## CONFIDENCE: HIGH
`l2cap_chan_close` internally calls `l2cap_chan_put`, releasing the work item’s reference; the subsequent `l2cap_chan_put` in `l2cap_chan_timeout` is an excess put leading to refcount underflow.
```
