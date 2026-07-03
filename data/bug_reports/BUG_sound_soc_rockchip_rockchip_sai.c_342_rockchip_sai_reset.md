# REAL BUG: sound/soc/rockchip/rockchip_sai.c:342 rockchip_sai_reset()

**Confidence**: HIGH | **Counter**: `$->deassert_count.counter`

## Reasoning

h the total asserts and deasserts inside the function are equal, they are ordered backwards relative to the required state. A correct reset sequence must first deassert (if not already deasserted) then assert. This unconditional assert-before-deassert is an excess put on already-asserted resets. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L346 (end of function) | void (success return) | YES (rst_h: L337 `reset_control_deassert(sai->rst_h)`, rst_m: L341 `reset_control_deassert(sai->rst_m)`) | YES (rst_h: L335 `reset_control_assert(sai->rst_h)`, rst_m: L339 `reset_control_assert(sai->rst_m)`) | NO ❌ EXCESS PUT | Function calls `assert` (PUT) before `deassert` (GET) on each reset. If the reset is already asserted (`deassert_count = 0`) when the function is entered, the first assert on each line underflows the counter ("excess put"). Even though the total asserts and deasserts inside the function are equal, they are ordered backwards relative to the required state. A correct reset sequence must first deassert (if not already deasserted) then assert. This unconditional assert-before-deassert is an excess put on already-asserted resets. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`reset_control_assert()` called before `reset_control_deassert()` on both `rst_h` and `rst_m`. If the reset lines are already asserted (common after probe), each assert causes a refcount underflow (`deassert_count` going negative), producing the "refcount excess put" warning. The sequence must be inverted or guarded with a status check.
```
