# REAL BUG: drivers/i2c/i2c-core-of-prober.c:367 i2c_of_probe_simple_enable()

**Confidence**: MEDIUM | **Counter**: `node->kobj.kref.refcount.refs.counter`

## Reasoning

- No ownership transfer or deferred cleanup can prevent this on the error path; the double put is a direct consequence of the cleanup chain.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L332 | error (no ctx/opts) | NO (before get) | N/A | ✅ | |
| L336 | error (no compat) | NO (before get) | N/A | ✅ | |
| L340-341 | error (no child found) | NO (conditional get failed, node NULL) | N/A | ✅ | |
| L345 | goto out_put_node (get_supply failed) | YES | YES (of_node_put at out_put_node) | ✅ | Only original reference released; no put_supply called |
| L349 | goto out_put_supply (get_gpiod failed) | YES | ⚠️ put_supply (may put node) + of_node_put | ❌ LIKELY DOUBLE PUT | If put_supply internally calls of_node_put(node) without an extra reference being taken, this path causes an excess put at L367 |
| L353 | goto out_put_gpiod (enable_regulator failed) | YES | ⚠️ put_gpiod → put_supply → of_node_put | ❌ Possible double put | Similar risk if any of these put functions release node |
| L357 | goto out_disable_regulator (set_gpio failed) | YES | ⚠️ disable_regulator → put_gpiod → put_supply → of_node_put | ❌ Possible double put | |
| L359 | success | YES | NO | ❌ LEAK (but not the warning) | Node not released; may be intentional lifetime hold, but not related to the excess-put warning |

**Analysis:**
- The warning is a `refcount excess put` at the `of_node_put(node)` on line 367.
- This indicates the node’s refcount was already zero at that point, i.e., the node had already been freed/underflown.
- The most plausible cause: on error paths after `get_supply` succeeds, `out_put_supply` calls `i2c_of_probe_simple_put_supply(ctx)`, and if that function itself performs an `of_node_put()` on the same `node` (perhaps because the supply context stored the node pointer **without** an extra `of_node_get()`), the subsequent fall‑through to `out_put_node` triggers a double put, causing the refcount underflow exactly at line 367.
- No ownership transfer or deferred cleanup can prevent this on the error path; the double put is a direct consequence of the cleanup chain.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM
`i2c_of_probe_simple_get_supply` likely stores the node pointer without an extra `of_node_get`, causing `i2c_of_probe_simple_put_supply` to do an unaccounted `of_node_put`; on the error path through `out_put_supply` the subsequent `of_node_put` at line 367 double-puts the node, leading to the `refcount excess put` warning.
```
