# REAL BUG: drivers/leds/flash/leds-aat1290.c:284 aat1290_led_parse_dt()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

wnership transferred to *sub_node but cleanup still fires, causing extra put | `*sub_node = child_node;` passes the reference out; the automatic `of_node_put` via `__free` then decrements the refcount, so the caller will later put an already‑released reference → double‑decrement / use‑after‑free |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L226 | error (gpio_fl_en) | NO (before get) | N/A | ✅ | |
| L233 | error (gpio_en_set) | NO (before get) | N/A | ✅ | |
| L250 | error (no child) | NO (get returned NULL) | N/A (of_node_put(NULL) safe) | ✅ | |
| L264 | error (flash-max-microamp) | YES | YES (via __free cleanup) | ✅ as intra‑function get/put pair; no ownership transfer | |
| L270 | error (flash-max-timeout-us) | YES | YES (via __free cleanup) | ✅ as intra‑function pair; no ownership transfer | |
| L275 | success (return 0) | YES | YES (via __free cleanup) | ❌ EXCESS PUT on success path – ownership transferred to *sub_node but cleanup still fires, causing extra put | `*sub_node = child_node;` passes the reference out; the automatic `of_node_put` via `__free` then decrements the refcount, so the caller will later put an already‑released reference → double‑decrement / use‑after‑free |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`of_get_next_available_child` acquires a reference; the `__free(device_node)` attribute unconditionally puts it on all exit paths, including the success path where `*sub_node = child_node;` transfers ownership to the caller without setting the local variable to NULL, causing a premature put and a subsequent double-decrement when the caller later releases the node.
```
