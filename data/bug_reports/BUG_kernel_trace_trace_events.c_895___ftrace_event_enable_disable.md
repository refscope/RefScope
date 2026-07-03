# REAL BUG: kernel/trace/trace_events.c:895 __ftrace_event_enable_disable()

**Confidence**: HIGH | **Counter**: `file->sm_ref.counter`

## Reasoning

4. goto between GET and PUT? No goto; break leaves without dec.

## Full Response

```
| Path Description | Line(s) | GET Done? (inc sm_ref)? | PUT Done? (dec sm_ref)? | Balanced? | Notes |
|-----------------|---------|-------------------------|-------------------------|-----------|-------|
| enable=0, soft_disable=false | ~L799-831 | No | No | ✅ | No sm_ref ops |
| enable=0, soft_disable=true, dec_return > 0 | ~L806 | No | Yes (dec) | ✅ | dec matches earlier inc |
| enable=0, soft_disable=true, dec_return == 0 | ~L806-832 | No | Yes (dec) | ✅ | |
| enable=1, soft_disable=false | ~L835 | No | No | ✅ | |
| enable=1, soft_disable=true, inc_return > 1 | ~L837 break | Yes (inc) | No | ✅ | Reference intentionally held |
| enable=1, soft_disable=true, inc_return == 1, event already enabled | ~L837 inc, ~L850 skip reg, break | Yes (inc) | No | ✅ | Reference intentionally held |
| enable=1, soft_disable=true, inc_return == 1, event not enabled, registration succeeds (ret=0) | ~L837 inc, ~L877 break | Yes (inc) | No | ✅ | Reference intentionally held |
| **enable=1, soft_disable=true, inc_return == 1, event not enabled, registration fails (ret ≠ 0)** | **~L837 inc, ~L870 break** | **Yes (inc)** | **No** | **❌ LEAK** | Error after inc leaves sm_ref incremented; no dec |

**Pre‑Verdict Checklist**
1. “Held for device lifetime”? Only on success. Error path returns before reference is properly established → must release. **Leak on error path.**  
2. “Ownership transferred”? Not applicable.  
3. Unconditional GET? Yes — `atomic_inc_return` always increments.  
4. goto between GET and PUT? No goto; break leaves without dec.  

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  

`atomic_inc_return(&file->sm_ref)` taken at ~L837 when `soft_disable && inc_return==1`. If the subsequent `call->class->reg()` fails, the function returns `ret` (negative) without calling `atomic_dec_return`, leaking the soft‑mode reference.
```
