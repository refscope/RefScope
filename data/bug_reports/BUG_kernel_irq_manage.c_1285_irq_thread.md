# REAL BUG: kernel/irq/manage.c:1285 irq_thread()

**Confidence**: HIGH | **Counter**: `$->threads_active.counter`

## Reasoning

| Function exit (after loop) | L1295 (return 0) | N/A (final state) | N/A | N/A | The loop body creates the imbalance; the return itself is unreachable until loop condition breaks, but the refcount may already be underflowed |

## Full Response

```
| Path (loop iteration scenario) | Line(s) | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| `action_ret == IRQ_WAKE_THREAD` | L1279, L1285 | YES (irq_wake_secondary) | YES (wake_threads_waitq) | ✅ | Balanced |
| `action_ret != IRQ_WAKE_THREAD` | L1279 (skipped), L1285 | NO (irq_wake_secondary not called) | YES (wake_threads_waitq) | ❌ EXCESS PUT | wake_threads_waitq decrements refcount without a prior increment |
| Function exit (after loop) | L1295 (return 0) | N/A (final state) | N/A | N/A | The loop body creates the imbalance; the return itself is unreachable until loop condition breaks, but the refcount may already be underflowed |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`irq_wake_secondary()` (conditional GET on `threads_active`) is only called when `action_ret == IRQ_WAKE_THREAD`, but `wake_threads_waitq()` (PUT) is called unconditionally afterwards, causing an excess put and refcount underflow every time the condition is false.
```
