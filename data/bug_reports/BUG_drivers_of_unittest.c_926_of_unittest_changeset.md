# REAL BUG: drivers/of/unittest.c:926 of_unittest_changeset()

**Confidence**: LOW | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

**Confidence**: LOW | **Counter**: `$->kobj.kref.refcount.refs.counter`

double put earlier. Get contracts show `of_find_node_by_path`/`of_get_child_by_name` acquire references, but without the function body we cannot trace whether a get was missing or whether a put on a node without a reference occurs. No ownership-transfer or devm pattern can explain an excess put. |

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| unknown | unknown | unknown | unknown | unknown | [NEED_SOURCE] of_unittest_changeset – main function source not provided; cannot enumerate paths. The warning “excess put” at L926 (on `$->kobj.kref.refcount.refs.counter`) indicates an `of_node_put` that decremented a refcount already at zero, strongly suggesting a missing `of_node_get` or a double put earlier. Get contracts show `of_find_node_by_path`/`of_get_child_by_name` acquire references, but without the function body we cannot trace whether a get was missing or whether a put on a node without a reference occurs. No ownership-transfer or devm pattern can explain an excess put. |

VERDICT: REAL_BUG
CONFIDENCE: LOW
Missing source prevents path enumeration, but the “excess put” on a kref counter typically signals an `of_node_put` on a node that either had no reference taken (missing get) or suffered an extra put; no false‑positive pattern (NULL put, deferred cleanup) removes the reference.
```
