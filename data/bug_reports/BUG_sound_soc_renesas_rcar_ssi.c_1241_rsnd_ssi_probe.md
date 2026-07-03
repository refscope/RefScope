# REAL BUG: sound/soc/renesas/rcar/ssi.c:1241 rsnd_ssi_probe()

**Confidence**: MEDIUM | **Counter**: `node->kobj.kref.refcount.refs.counter`

## Reasoning

he contracts and very likely returns a stored pointer without incrementing the refcount (e.g., `priv->ssi_node`). The `of_node_put` call is therefore redundant and triggers an excess put, as reported by smatch. The warning line (≈1236) is the exact `of_node_put(node)` inside `rsnd_ssi_probe_done`.

## Full Response

```
[NEED_SOURCE] rsnd_ssi_of_node

```
| Line | Return Type          | GET Done?                 | PUT Done?       | Balanced? | Notes                                                                     |
|------|----------------------|---------------------------|-----------------|-----------|---------------------------------------------------------------------------|
| 1170 | early return         | NO (node is NULL)         | NO (skipped)    | ✅         | early exit, no ref held                                                   |
| 1176 | goto done (nr==0)    | NO (source not a GET)     | YES (of_node_put) | ❌ EXCESS | of_node_put called without matching get → ref underflow                   |
| 1182 | goto done (alloc fail)| NO                       | YES             | ❌ EXCESS | same as above                                                             |
| 1198 | goto done (index err) | NO                       | YES             | ❌ EXCESS |                                                                           |
| 1205 | goto done (clk err)  | NO                       | YES             | ❌ EXCESS |                                                                           |
| 1212 | goto done (irq err)  | NO                       | YES             | ❌ EXCESS |                                                                           |
| 1224 | goto done (mod err)  | NO                       | YES             | ❌ EXCESS |                                                                           |
| 1236 | success fall-through | NO                       | YES             | ❌ EXCESS |                                                                           |
```

All goto/fall-through paths after node is obtained execute `of_node_put(node)`, but there is no visible reference acquisition on `node`. The function `rsnd_ssi_of_node(priv)` is not documented in the contracts and very likely returns a stored pointer without incrementing the refcount (e.g., `priv->ssi_node`). The `of_node_put` call is therefore redundant and triggers an excess put, as reported by smatch. The warning line (≈1236) is the exact `of_node_put(node)` inside `rsnd_ssi_probe_done`.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM

`rsnd_ssi_of_node` likely does not acquire a reference, making the unconditional `of_node_put(node)` an excess put on every non-NULL path.
```
