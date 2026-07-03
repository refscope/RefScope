# REAL BUG: drivers/leds/leds-lp8860.c:332 lp8860_probe()

**Confidence**: LOW | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

led in an error path where the node was already released by another mechanism, or because two puts exist on a single path. To determine whether the excess put is a real bug, we need to see the full function body, including the code around line 332.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L280 (if (!child_node)) | error (return -EINVAL) | NO (child_node NULL → no ref held) | N/A | ✅ | of_get_next_available_child returned NULL, no increment |
| L285 (IS_ERR(enable_gpio)) | error (return dev_err_probe) | YES | **NO** (no of_node_put visible) | ❌ LEAK | child_node ref not released |
| L289 (vled regulator enable ret != -ENODEV) | error (return dev_err_probe) | YES | **NO** | ❌ LEAK | child_node ref not released |
| L294 (devm_mutex_init failure) | error (return dev_err_probe) | YES | **NO** | ❌ LEAK | child_node ref not released |
| L299 (regmap init failure) | error (return ret) | YES | **NO** | ❌ LEAK | child_node ref not released |
| L304 (program_eeprom && ret) | error (return ret) | YES | **NO** | ❌ LEAK | child_node ref not released |
| L312 (devm_led_classdev_register_ext failure) | error (return ret) | YES | **NO** | ❌ LEAK | child_node ref not released |
| L318 (return 0) | success (return 0) | YES | **NO** | ❌ LEAK | child_node ref not released |

**IMPORTANT**: The provided source snippet ends at `return 0; }`. The warning line 332 is **beyond the end of the shown code**, indicating there are additional statements (likely an `of_node_put(child_node)`) in the actual function that are missing from the snippet. The warning type is **excess put**, not a leak. This means there is a put operation that happens more times than gets, likely because an `of_node_put` is called in an error path where the node was already released by another mechanism, or because two puts exist on a single path. To determine whether the excess put is a real bug, we need to see the full function body, including the code around line 332.

[NEED_SOURCE] drivers/leds/leds-lp8860.c 320 340

VERDICT: UNCLEAR
CONFIDENCE: LOW
Lost path at warning line 332: required source beyond provided snippet to see of_node_put and confirm double-put scenario.
```
