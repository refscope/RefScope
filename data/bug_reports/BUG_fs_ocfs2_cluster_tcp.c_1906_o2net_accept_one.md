# REAL BUG: fs/ocfs2/cluster/tcp.c:1906 o2net_accept_one()

**Confidence**: MEDIUM | **Counter**: `$->nd_item.ci_kref.refcount.refs.counter`

## Reasoning

**Request**: `[NEED_SOURCE] sc_alloc` – to confirm whether the internal `o2nm_node_get` is indeed unconditional on error path, but given the contract the analysis assumes it is.

## Full Response

```
| Line | Return Type | GET Done? | PUT Done? | Balanced? | Notes |
|------|-------------|-----------|-----------|-----------|-------|
| L1805 | error (sock_create_lite fail) | NO | N/A | ✅ | before any get |
| L1811 | error (accept fail) | NO | N/A | ✅ | no node or sc yet |
| L1821 | error (getname fail) | NO | N/A | ✅ | node not obtained |
| L1829 | error (node==NULL) | NO (get failed) | N/A | ✅ | node NULL, no put needed |
| L1837 | error (o2nm_this_node check) | YES (node + local_node if non‑NULL) | YES (both put at out) | ✅ | local_node ref balanced |
| L1845 | error (heartbeating false) | YES (node) | YES (put at out) | ✅ | |
| L1858 | error (nn_sc already exists) | YES (node) | YES (put at out) | ✅ | |
| L1864 | error (sc_alloc returns NULL) | YES (node from o2nm_get_node_by_ip) <br> **ADDITIONAL GET**: sc_alloc contract says unconditional → o2nm_node_get(get) ⇒ YES (extra ref) | PUT for original node ref (o2nm_node_put at out) <br> **NO PUT** for sc_alloc’s extra ref (sc == NULL → sc_put not called) | ❌ LEAK | If sc_alloc unconditionally called o2nm_node_get before returning NULL, one reference is leaked |
| L1879+ | success | YES (node + sc refs) | YES (put node, sc_put) | ✅ | |

**Analysis**:  
- `o2nm_get_node_by_ip` is conditional → only leaks if `node` not NULL; at out we always `o2nm_node_put(node)` when non‑NULL → balanced.  
- `sc_alloc` contract states `unconditional; →o2nm_node_get(get)`. Following the audit rule, this means sc_alloc **always** increments the node’s refcount, even on allocation failure.  
- On the `sc == NULL` path, the extra reference acquired by `sc_alloc` is never released (no `sc_put` because `sc` is NULL, and the out‑label only puts the original `o2nm_get_node_by_ip` reference). → Unbalanced.

**Request**: `[NEED_SOURCE] sc_alloc` – to confirm whether the internal `o2nm_node_get` is indeed unconditional on error path, but given the contract the analysis assumes it is.

VERDICT: REAL_BUG  
CONFIDENCE: MEDIUM  
sc_alloc allegedly takes an unconditional node reference; the `sc==NULL` error path forgets to release it, causing a refcount leak.
```
