# REAL BUG: drivers/net/ethernet/mellanox/mlxsw/spectrum_ptp.c:1277 mlxsw_sp1_ptp_hwtstamp_set()

**Confidence**: HIGH | **Counter**: `$->mlxsw_sp->parsing.parsing_depth_ref.refs.counter`

## Reasoning

ceeded, parsing depth incremented) | NO | ❌ LEAK | No rollback of the parsing depth reference; error path returns without decrement |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| ~L1258 | error (before `mlxsw_sp1_ptp_mtpppc_update`) | NO | N/A | ✅ | No parsing depth reference acquired |
| ~L1263 | error (`mlxsw_sp1_ptp_mtpppc_update` fails) | NO (assuming update cleans up on error) | N/A | ✅ | Conditional on path — should not leave a net reference |
| ~L1270 | error (`mlxsw_sp1_ptp_port_shaper_check` fails) | YES (update succeeded, parsing depth incremented) | NO | ❌ LEAK | No rollback of the parsing depth reference; error path returns without decrement |
| ~L1276 | success | YES | Not required (ownership transfer) | ✅ | Reference held for the lifetime of the PTP configuration; released later when config is cleared |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`mlxsw_sp1_ptp_mtpppc_update()` successfully increments the parsing depth reference, but the subsequent error from `mlxsw_sp1_ptp_port_shaper_check()` returns without decrementing it — no rollback against the acquired reference.
```
