# REAL BUG: drivers/accel/habanalabs/common/command_submission.c:1875 hl_cs_signal_sob_wraparound_handler()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

nction then returns `other_sob` to the caller via `*hw_sob = other_sob`. The caller (or later code) will subsequently `hw_sob_put` the object, causing a kref underflow – exactly the “refcount excess put” reported.

## Full Response

```
| Line | Return Type | GET sob? | PUT sob? | GET other_sob? | PUT other_sob? | Balanced? | Notes |
|-------|-------------|-----------|----------|----------------|----------------|-----------|-------|
| L1827 | error (-EINVAL) | YES (L1) | YES (L2) | NO | NO | ✅ | sob balanced; no other_sob touched |
| L1875 (else) | success | YES (L1) | NO | NO | NO | ❌ LEAK on sob (extra get never put) | non‑wraparound path |
| L1875 (wraparound, need_reset=false) | success | YES (L1) | YES (L2) | NO | NO | ✅ | sob balanced; other_sob ref=1, caller will safely put |
| L1875 (wraparound, need_reset=true, encaps_sig=true) | success | YES (L1) | YES (L2) | YES (L4) | YES (L3) | ✅ | other_sob ref: 0→1, balanced |
| L1875 (wraparound, need_reset=true, encaps_sig=false) | success | YES (L1) | YES (L2) | **NO** (L4 skipped) | **YES** (L3) | ❌ EXCESS PUT on other_sob | other_sob refcount becomes 0, no get, later caller put will underflow |

- L1 = `hw_sob_get(sob)`  
- L2 = `hw_sob_put_err(sob)`  
- L3 = `hw_sob_put(other_sob)` (inside `need_reset`)  
- L4 = `hw_sob_get(other_sob)` (inside `encaps_sig`)  

The function unconditionally gets a reference on the original `sob` (L1) and conditionally puts it back on the wraparound path (L2).  
On the wraparound success path where `other_sob->need_reset` is true and `encaps_sig` is false, the function calls `hw_sob_put(other_sob)` (bringing its kref to 0) but does **not** follow with a matching `hw_sob_get(other_sob)`.  
The function then returns `other_sob` to the caller via `*hw_sob = other_sob`. The caller (or later code) will subsequently `hw_sob_put` the object, causing a kref underflow – exactly the “refcount excess put” reported.

No ownership transfer, devm cleanup, IS_ERR guard, or async deferral corrects this.

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

Missing `hw_sob_get(other_sob)` after reset when `encaps_sig==false` leaves other_sob with kref == 0, leading to a later excess put (underflow).
```
