# REAL BUG: drivers/bus/mhi/host/pci_generic.c:1115 mhi_pci_status_cb()

**Confidence**: HIGH | **Counter**: `$->power.usage_count.counter`

## Reasoning

through | NO | YES (`pm_runtime_allow`) | ❌ EXCESS PUT | Put executed without any matching get in this invocation; caller may not have called forbid before, causing refcount underflow. This is the warning at line 1115. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1105 (case MHI_CB_FATAL_ERROR) | void fall-through | YES (`pm_runtime_forbid`) | NO | N/A | Get acquired, no put in this invocation; expected to be paired later. |
| L1105 (case MHI_CB_SYS_ERROR) | void fall-through | YES | NO | N/A | Same. |
| L1109 (case MHI_CB_EE_MISSION_MODE) | void fall-through | NO | YES (`pm_runtime_allow`) | ❌ EXCESS PUT | Put executed without any matching get in this invocation; caller may not have called forbid before, causing refcount underflow. This is the warning at line 1115. |
| L1112 (default) | void fall-through | NO | NO | N/A | No refcount change. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`pm_runtime_allow()` at L1109 may be called without a prior `pm_runtime_forbid()` (e.g., first callback with MHI_CB_EE_MISSION_MODE), causing an excess put on the device's runtime PM usage counter. No state is tracked to prevent unprotected allow.
```
