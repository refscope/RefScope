# REAL BUG: kernel/time/posix-cpu-timers.c:1565 do_cpu_nanosleep()

**Confidence**: HIGH | **Counter**: `$->it.cpu.pid->count.refs.counter`

## Reasoning

| L1565   | error (final) | NO (creation failed) or YES (but del already called earlier) | N/A if creation failed, otherwise YES | ✅ | if creation failed → no ref; if creation succeeded → del already executed; balanced |

## Full Response

```
```
| Line    | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|---------|-------------|-----------|-----------|-----------|-------|
| L1502   | error       | YES       | NO        | ❌ LEAK   | posix_cpu_timer_create succeeded → holds pid ref; set fails; returns without posix_cpu_timer_del |
| L1508   | success (0) | YES       | YES       | ✅        | del called before this return inside while loop |
| L1530   | success (0) | YES       | YES       | ✅        | del called earlier in signal path, then this return |
| L1565   | error (final) | NO (creation failed) or YES (but del already called earlier) | N/A if creation failed, otherwise YES | ✅ | if creation failed → no ref; if creation succeeded → del already executed; balanced |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
posix_cpu_timer_create takes a pid ref; on posix_cpu_timer_set error we return at line ~1502 without calling posix_cpu_timer_del → leak.
```
```
