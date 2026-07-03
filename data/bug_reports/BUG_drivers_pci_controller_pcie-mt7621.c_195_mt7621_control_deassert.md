# REAL BUG: drivers/pci/controller/pcie-mt7621.c:195 mt7621_control_deassert()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

| `resets_inverted == false`  | void return | NO                                   | YES (line 195)                   | ❌                                   | Assert (put) called when deassert is expected → refcount underflow. |

## Full Response

```
| Path                        | Return Type | GET Done? (reset_control_deassert) | PUT Done? (reset_control_assert) | Balanced? (relative to expectation) | Notes |
|-----------------------------|-------------|--------------------------------------|----------------------------------|--------------------------------------|-------|
| `resets_inverted == true`   | void return | YES (line 193)                       | NO                               | ✅                                   | Deassert (get) matches function name. |
| `resets_inverted == false`  | void return | NO                                   | YES (line 195)                   | ❌                                   | Assert (put) called when deassert is expected → refcount underflow. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`mt7621_control_deassert()` calls `reset_control_assert()` (put) on the `resets_inverted == false` path, which contradicts the function's “deassert” intent and causes an excess put (refcount underflow) on line 195.
```
