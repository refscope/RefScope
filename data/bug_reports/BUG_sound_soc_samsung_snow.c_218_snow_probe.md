# REAL BUG: sound/soc/samsung/snow.c:218 snow_probe()

**Confidence**: HIGH | **Counter**: `link->codecs.of_node.kobj.kref.refcount.refs.counter`

## Reasoning

| `return 0;` (L203) | success | YES | NO (intentional) | ✅ | Ref held for card lifetime; cleanup via devm / card deregistration. |

## Full Response

```
| Line (approx) | Return Type | GET Done? (snd_soc_of_get_dai_link_codecs) | PUT Done? (snd_soc_of_put_dai_link_codecs) | Balanced? | Notes |
|---------------|-------------|--------------------------------------------|--------------------------------------------|-----------|-------|
| after `if (!link->cpus->of_node)` (L146) | error return -EINVAL | NO (GET not yet called) | N/A | ✅ | No leak, GET hasn’t happened. |
| after `if (ret < 0)` (L156) | error return `ret` | **YES** (unconditional GET, refs held even on error) | **NO** | ❌ **LEAK** | Missing `snd_soc_of_put_dai_link_codecs(link)`; only `of_node_put(link->cpus->of_node)` is called. |
| after `if (IS_ERR(priv->clk_i2s_bus))` (L163) | error return `PTR_ERR(...)` | YES | YES | ✅ | Balanced – `snd_soc_of_put_dai_link_codecs(link)` called. |
| after `if (ret) return dev_err_probe(...)` (end of probe, ~L200) | error return | **YES** (GET earlier in same block) | **NO** | ❌ **LEAK** | Register card failure; the codecs’ of_node refs obtained by GET are never released. |
| `return 0;` (L203) | success | YES | NO (intentional) | ✅ | Ref held for card lifetime; cleanup via devm / card deregistration. |

**VERDICT: REAL_BUG**  
**CONFIDENCE: HIGH**  

`snd_soc_of_get_dai_link_codecs()` is an unconditional get that always increments codec of_node refs. The error exit when it returns < 0 (line ~156) does not call `snd_soc_of_put_dai_link_codecs(link)`, leaking the references. Additionally, the later `devm_snd_soc_register_card` failure path also omits the required put.
```
