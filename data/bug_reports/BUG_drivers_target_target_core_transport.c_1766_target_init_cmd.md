# REAL BUG: drivers/target/target_core_transport.c:1766 target_init_cmd()

**Confidence**: HIGH | **Counter**: `se_cmd->cmd_kref.refcount.refs.counter`

## Reasoning

| L1766 (target_get_sess_cmd returns < 0) | error | YES (kref_init performed unconditionally) | NO – no kref_put on error | ❌ LEAK | __target_init_cmd sets kref to 1; error path does not release it |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1766 (target_get_sess_cmd returns 0) | success | YES (kref_init performed unconditionally) | N/A – init ref held for command lifetime | ✅ | Successful initialization, no leak |
| L1766 (target_get_sess_cmd returns < 0) | error | YES (kref_init performed unconditionally) | NO – no kref_put on error | ❌ LEAK | __target_init_cmd sets kref to 1; error path does not release it |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`__target_init_cmd()` unconditionally initialises `cmd_kref` to 1. If the following `target_get_sess_cmd()` returns an error, the function returns immediately without a `kref_put`, leaking the initial reference.
```
