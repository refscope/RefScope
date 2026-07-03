# REAL BUG: arch/x86/kernel/devicetree.c:135 dtb_cpu_setup()

**Confidence**: MEDIUM | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

**Contract detail**: `of_node_to_nid` is unconditional and performs `→of_node_put(put)`.  Combined with the loop’s increment step which also puts the node, every valid (non‑skipped) node triggers a double release.  This matches the “refcount excess put” warning.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L135 (continue path) | continue (jumps to increment) | YES (of_get_next_cpu_node at start of iteration) | YES (increment step: of_get_next_cpu_node(dn) puts dn) | ✅ | of_node_to_nid not called, single put matches get |
| L139‑L142 (normal path, after set_apicid_to_node) | loop iteration complete, then increment | YES (of_get_next_cpu_node at start) | YES (by of_node_to_nid internally) + YES (increment step puts again) ⚠️ | ❌ | of_node_to_nid’s contract says it calls of_node_put, causing first put; increment step causes second put → **excess put** |
| Loop exit (final increment returns NULL) | function returns | depends on last node | same imbalance if last node was valid | ❌ | if last node took normal path, double put already happened; function leaks no reference but triggers excess put on those nodes |

**Contract detail**: `of_node_to_nid` is unconditional and performs `→of_node_put(put)`.  Combined with the loop’s increment step which also puts the node, every valid (non‑skipped) node triggers a double release.  This matches the “refcount excess put” warning.

VERDICT: REAL_BUG
CONFIDENCE: MEDIUM

```
of_node_to_nid(dn) internally puts dn, then the loop’s next of_get_next_cpu_node(dn) puts it again, causing an excess put on every CPU node with a valid apic_id.
```
```
