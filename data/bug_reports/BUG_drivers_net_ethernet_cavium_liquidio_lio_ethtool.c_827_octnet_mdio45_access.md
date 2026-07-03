# REAL BUG: drivers/net/ethernet/cavium/liquidio/lio_ethtool.c:827 octnet_mdio45_access()

**Confidence**: HIGH | **Counter**: `$->sc_buf_pool.alloc_buf_count.counter`

## Reasoning

| success path: WRITE_ONCE(… caller_is_done); return retval (0) | success | YES | NO | ❌ LEAK | no free |

## Full Response

```
| Line (description) | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| if (!sc) return -ENOMEM | error | NO (alloc failed) | N/A | ✅ | |
| IQ_SEND_FAILED case: free; return -EBUSY | error | YES | YES | ✅ | octeon_free_soft_command called |
| wait_for_sc_completion_timeout non‑zero, return retval | success (completion) | YES | NO | ❌ LEAK | no free |
| mdio_cmd_rsp->status error: WRITE_ONCE(… caller_is_done); return -EBUSY | error | YES | NO | ❌ LEAK | no free |
| success path: WRITE_ONCE(… caller_is_done); return retval (0) | success | YES | NO | ❌ LEAK | no free |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
octnet_mdio45_access() leaks octeon_alloc_soft_command on all paths except IQ_SEND_FAILED; missing octeon_free_soft_command on timeout, mdio status error, and success returns.
```
