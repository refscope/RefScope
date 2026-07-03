# REAL BUG: net/sctp/stream.c:479 sctp_send_add_streams()

**Confidence**: LOW | **Counter**: `$->refcnt.refs.counter`

## Reasoning

Once I have that, I can determine if the success path in `sctp_send_add_streams` is missing a `sctp_chunk_put` (leak) or if the error path’s `sctp_chunk_put` is the only necessary put and the “excess put” warning is a false positive caused by unpatched static analysis misinterpreting the ownership t

## Full Response

```
## Path Table

Based on the provided source for `sctp_send_add_streams()`, all return paths are through the `out:` label which falls through to `return retval;`. I list every possible execution path that reaches a `goto out` (or fall-through after success).

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L436 | error (ENOPROTOOPT) | NO (GET never executed) | N/A | ✅ | |
| L441 | error (EINPROGRESS) | NO | N/A | ✅ | |
| L451 | error (EINVAL) | NO | N/A | ✅ | |
| L457 | error (stream_alloc_out failure) | NO | N/A | ✅ | Stream alloc failure before any GET on the chunk |
| L463 | error (ENOMEM) | NO | N/A | ✅ | chunk allocation failed; no GET |
| L473 | error (send_reconf failure) | YES (unconditional sctp_chunk_hold at L467) | YES (sctp_chunk_put at L471) | ✅ | Explicit put on the error path |
| L479 | success | YES | NO ⚠️ | ❌ LEAK or potential double‑put depending on callee | No put on this path; ref held forever or caller relies on callee-consuming the extra ref – see analysis |

The only path where GET=YES is the one that reaches `sctp_chunk_hold` and then calls `sctp_send_reconf`. On **success** (retval == 0, line 479) there is **no corresponding sctp_chunk_put** in this function. Whether this is a real bug depends on whether `sctp_send_reconf` on success already consumed the chunk reference, making the extra `hold` unnecessary (and thus the missing `put` would be a leak) **or** whether `sctp_send_reconf` itself does a put that would cause a double‑put if we added a `put` here. The warning is about an **excess put**, which points to a scenario where a put is called more times than the gets.

## Detailed Analysis

### Contracts Recap
- **`sctp_chunk_hold`** – unconditional, always increments the chunk’s refcount.
- **`sctp_chunk_put`** – unconditional, decrements and frees when zero.
- **`sctp_send_reconf`** – conditional on path; can call `sctp_chunk_free()` (i.e., *put*) along some paths.

### Crucial Unknown: sctp_send_reconf Internals
The warning (**refcount excess put**) would arise if `sctp_send_reconf` **already drops a reference** on the success path, making the caller’s `hold` a double‑hold and the **absence** of a `put` in the success path correct (the chunk’s reference would be correctly managed). On the other hand, if `sctp_send_reconf` does **not** drop a reference on success, then the missing `put` in the success path would be a **leak**, not an excess put. The “excess put” warning is about a put that shouldn’t be there, not a missing put.

The line number 479 is the function’s `return retval;`. Smatch often flags the point where the imbalance becomes apparent (the function exit) when a put that would trigger underflow originates from a caller. In this case, the warning likely indicates that **on the success path**, after `sctp_send_add_streams` returns, an *extra* put is performed somewhere (maybe in the layer that receives the chunk from `sct
```
