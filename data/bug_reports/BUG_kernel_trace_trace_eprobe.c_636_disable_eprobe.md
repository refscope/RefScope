# REAL BUG: kernel/trace/trace_eprobe.c:636 disable_eprobe()

**Confidence**: MEDIUM | **Counter**: `$->tm_ref.counter`

## Reasoning

| L636 | success (return 0) | NO in this function, but expected from prior enable | YES (`trace_event_trigger_enable_disable(file, 0)`) | ❌ EXCESS PUT | Warning at this line: refcount already 0 → double-put |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L602 | error (ENOENT) | NO | NO | ✅ | no trigger found |
| L615 | error (ENODEV) | NO | NO | ✅ | no matching trigger |
| L636 | success (return 0) | NO in this function, but expected from prior enable | YES (`trace_event_trigger_enable_disable(file, 0)`) | ❌ EXCESS PUT | Warning at this line: refcount already 0 → double-put |

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  

`disable_eprobe()` unconditionally calls `trace_event_trigger_enable_disable(file, 0)` on a trigger it removes from the list, but if the trigger is already disabled (e.g., externally detached), this PUT will push an already‑zero `tm_ref.counter` below zero, causing the reported excess‑put.
```
