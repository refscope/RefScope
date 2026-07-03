# REAL BUG: drivers/mailbox/qcom-ipcc.c:255 qcom_ipcc_setup_mbox()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L255 | return (devm_mbox_controller_register) | Same as above, plus leaked `client_dn` references from `for_each_node_with_property` macro (leak, not excess put). | Same stale `of_node_put(curr_ph.np)` as above. | ❌ EXCESS PUT | Same double-put bug as at L239. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L239 | early return (0) | Potentially multiple GETs from successful `of_parse_phandle_with_args()` in earlier loop iterations; GET from failed call is not done (np not set). | Unconditional `of_node_put(curr_ph.np)` on every iteration, including stale pointer after a failure in a later iteration (when `ret != 0` and `curr_ph.np` still holds previous node). | ❌ EXCESS PUT | After a successful iteration, `curr_ph.np` is set and put. If a subsequent iteration’s `of_parse_phandle_with_args()` fails, `curr_ph.np` is unchanged (stale). The unconditional `of_node_put` puts that already-released node again, causing a refcount underflow (excess put). |
| L255 | return (devm_mbox_controller_register) | Same as above, plus leaked `client_dn` references from `for_each_node_with_property` macro (leak, not excess put). | Same stale `of_node_put(curr_ph.np)` as above. | ❌ EXCESS PUT | Same double-put bug as at L239. |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Unconditional `of_node_put(curr_ph.np)` after `of_parse_phandle_with_args()` uses a stale pointer when the call fails (ret != 0), causing a double put and refcount underflow.
```
