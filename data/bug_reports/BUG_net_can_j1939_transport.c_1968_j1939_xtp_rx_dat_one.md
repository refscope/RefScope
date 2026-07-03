# REAL BUG: net/can/j1939/transport.c:1968 j1939_xtp_rx_dat_one()

**Confidence**: HIGH | **Counter**: `$->kref.refcount.refs.counter`

## Reasoning

| ~1930 | normal return (else)    | NO                         | YES (explicit at L1968)                                                   | ✅        | Only caller reference released. |

## Full Response

```
| Line | Return Type           | GET Done?                  | PUT Done?                                                                           | Balanced? | Notes |
|------|-----------------------|----------------------------|-------------------------------------------------------------------------------------|-----------|-------|
| ~1854 | goto out_session_cancel | NO (before any get)        | N/A (out_session_cancel block runs timers_cancel, session_cancel, then session_put) | ✅        | No internal get; caller ref consumed. If session_cancel puts (likely), this path would double-put but not the line warned. |
| ~1875 | goto out_session_cancel | NO                         | N/A                                                                                 | ✅        | Same as above. |
| ~1888 | goto out_session_cancel | NO                         | N/A                                                                                 | ✅        | |
| ~1899 | goto out_session_cancel | NO                         | N/A                                                                                 | ✅        | |
| ~1911 | goto out_session_cancel | NO                         | N/A                                                                                 | ✅        | |
| ~1930 | normal return (final)   | NO                         | YES: `j1939_session_completed()` (internally does a put) + explicit `j1939_session_put()` at L1968 → **double put** | ❌ EXCESS PUT | After `session_completed` drops its reference, the explicit put tries to drop an already zero reference → underflow. This matches the warning on `$->kref` at line 1968. |
| ~1930 | normal return (remain)  | NO                         | YES (explicit at L1968)                                                   | ✅        | Only caller reference released. |
| ~1930 | normal return (do_cts_eoma) | YES (`j1939_tp_schedule_txtimer`) | YES (explicit at L1968)                                                       | ✅ (note) | `schedule_txtimer` holds an extra ref for the timer; not released here (expected, owned by timer). No excess put. |
| ~1930 | normal return (else)    | NO                         | YES (explicit at L1968)                                                   | ✅        | Only caller reference released. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH

The `final` path of `j1939_xtp_rx_dat_one()` first calls `j1939_session_completed(session)`, which internally releases a reference to the session via `j1939_session_put`. Subsequently the function unconditionally calls `j1939_session_put(session)` again at line 1968, resulting in a double‑put that over-decrements the kref and triggers the “refcount excess put” warning.
```
