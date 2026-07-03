# REAL BUG: drivers/clk/renesas/renesas-cpg-mssr.c:1243 cpg_mssr_reserved_init()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

S (every reserved child processed via `of_get_next_reserved_child`) | NO (no `of_node_put` on any child) | ❌ LEAK | All child references obtained by the iterator are lost when the loop overwrites 'node' and when it terminates with NULL; the function returns with those refcounts never decremented |

## Full Response

```
```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1218 | error (-ENOMEM) | YES (for_each_reserved_child_of_node grants a ref on 'node' in current iteration) | NO ('node' not put) | ❌ LEAK | The reserved child's reference is never released; also the `of_node_put(it.node)` here may be spurious if the phandle iterator didn't obtain a reference, but the child leak remains |
| L1243 | success (return 0) | YES (every reserved child processed via `of_get_next_reserved_child`) | NO (no `of_node_put` on any child) | ❌ LEAK | All child references obtained by the iterator are lost when the loop overwrites 'node' and when it terminates with NULL; the function returns with those refcounts never decremented |

VERDICT: REAL_BUG
CONFIDENCE: HIGH
Each reserved child's reference obtained by for_each_reserved_child_of_node is leaked on every exit path because the iterator does not automatically release them and the code never calls of_node_put on the iterated node.
```
