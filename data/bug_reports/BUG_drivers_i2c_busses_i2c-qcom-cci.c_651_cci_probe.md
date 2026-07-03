# REAL BUG: drivers/i2c/busses/i2c-qcom-cci.c:651 cci_probe()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| L620 | return ret (via disable_clocks) | YES | NO | ❌ LEAK | from error/disable_clocks |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L526 | return -ENOMEM | NO (before loop) | N/A | ✅ | |
| L531 | return -ENOENT | NO (before loop) | N/A | ✅ | |
| L566 | return PTR_ERR | YES (for_each child ref + of_node_get) | NO | ❌ LEAK | child ref from loop, stored master refs leaked |
| L569 | return dev_err_probe | YES | NO | ❌ LEAK | same |
| L571 | return dev_err_probe | YES | NO | ❌ LEAK | same |
| L575 | return ret | YES | NO | ❌ LEAK | after cci_enable_clocks, no put |
| L578 | goto disable_clocks | YES | NO | ❌ LEAK | disable_clocks does no of_node_put |
| L583 | goto disable_clocks | YES | NO | ❌ LEAK | same |
| L589 | goto error | YES | NO | ❌ LEAK | error/disable_clocks skip all puts |
| L592 | goto error | YES | NO | ❌ LEAK | same |
| L603 | goto error_i2c | YES (macro child ref) | PARTIAL (masters 0..i-1 put, child ref not put) | ❌ LEAK | for_each child ref never released |
| L606 | return 0 | YES (macro child ref) | NO | ❌ LEAK | success path also leaks child ref |
| L620 | return ret (via disable_clocks) | YES | NO | ❌ LEAK | from error/disable_clocks |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
`for_each_available_child_of_node` holds a reference on each child; after the loop the final child (and any stored `of_node_get(child)`) is never released on any return path. The missing `of_node_put(child)` leaks the reference in all post‑loop exits including the success path.
```
