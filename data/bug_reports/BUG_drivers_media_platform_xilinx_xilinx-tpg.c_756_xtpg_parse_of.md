# REAL BUG: drivers/media/platform/xilinx/xilinx-tpg.c:756 xtpg_parse_of()

**Confidence**: HIGH | **Counter**: `$->kobj.kref.refcount.refs.counter`

## Reasoning

*If `nports == 0` (no ports in DT), the loop body never runs and no reference is acquired; the subsequent `nports` check returns early without a leak, but this single safe path does not cover the leaking paths shown above.*

## Full Response

```
## Path Table

| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L722-723 | error (PTR_ERR(format)) | YES | NO | ❌ LEAK | port ref from of_graph_get_next_port not released before return |
| L728-729 | error (-EINVAL) | YES | NO | ❌ LEAK | same – port ref held, return without of_node_put(port) |
| L742-744 | error (-EINVAL) | YES | NO | ❌ LEAK | after loop, last port node’s reference was never released |
| L750     | success (return 0) | YES | NO | ❌ LEAK | last port node’s reference leaked |

*If `nports == 0` (no ports in DT), the loop body never runs and no reference is acquired; the subsequent `nports` check returns early without a leak, but this single safe path does not cover the leaking paths shown above.*

## VERDICT: REAL_BUG  
## CONFIDENCE: HIGH  
**Reason:** `for_each_of_graph_port` acquires a reference on each port node, but `of_node_put(port)` is never called – all exit paths that encounter a port leak the reference.
```
