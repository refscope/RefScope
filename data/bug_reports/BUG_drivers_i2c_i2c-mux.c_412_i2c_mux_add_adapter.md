# REAL BUG: drivers/i2c/i2c-mux.c:412 i2c_mux_add_adapter()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

| ~L412 (success)          | return 0 | YES (if of_node present) | YES (reference stored in `priv->adap.dev.of_node`, expected to be released on device removal) | ✅ | ownership transferred to adapter device |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L277 | error (return -EINVAL) | NO (before OF block) | N/A | ✅ | early check, no refs taken |
| L282 | error (return -ENOMEM) | NO (before OF block) | N/A | ✅ | allocation failure, no refs taken |
| ~L390 (i2c_add_numbered_adapter failure) | goto err_free_priv | YES (if `muxc->dev->of_node` non‑NULL and `child` obtained) | NO (`err_free_priv` only does `kfree(priv)`) | ❌ LEAK | leaked `child` device_node reference; `err_free_priv` lacks `of_node_put` |
| ~L400 (i2c_add_adapter failure) | goto err_free_priv | YES (same as above) | NO (same) | ❌ LEAK | same leak on this path |
| ~L412 (success)          | return 0 | YES (if of_node present) | YES (reference stored in `priv->adap.dev.of_node`, expected to be released on device removal) | ✅ | ownership transferred to adapter device |

VERDICT: REAL_BUG  
CONFIDENCE: HIGH  
`child` device_node reference acquired in the OF block is stored in `priv->adap.dev.of_node`, but the error paths after failed adapter registration (`goto err_free_priv`) only `kfree(priv)` without releasing that reference, causing a refcount leak.
```
